#!/usr/bin/env python3
"""Convert audited Dukascopy bid/ask ticks into MT5 custom-symbol import CSVs.

The output is an import preparation artifact only. It does not connect to MT5,
create symbols, run Strategy Tester, or place orders. Run the tick audit first.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from research.evolution.audit_dukascopy_tick_archive import audit

MT5_BID_ASK_FLAGS = 2 | 4


def as_utc(value, timestamp_type) -> datetime:
    if value is None:
        raise ValueError("Null tick timestamp")
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif isinstance(value, (int, float)):
        import pandas as pd
        magnitude = abs(float(value))
        unit = "ns" if magnitude > 1e17 else "us" if magnitude > 1e14 else "ms" if magnitude > 1e11 else "s"
        dt = pd.to_datetime(value, unit=unit, utc=True).to_pydatetime()
    else:
        raise TypeError(f"Unsupported timestamp value: {type(value).__name__}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def convert(data_root: Path, output_root: Path, batch_size: int = 100_000) -> dict:
    report = audit(data_root, batch_size=batch_size)
    if report["quality_gate"] != "PASS":
        raise ValueError("Tick audit failed; MT5 conversion blocked")
    files = sorted(data_root.rglob("*.parquet"))
    output_root.mkdir(parents=True, exist_ok=True)
    writers = {}
    rows = 0
    previous = None
    try:
        for file in files:
            pf = pq.ParquetFile(file)
            names = set(pf.schema_arrow.names)
            if not {"time", "bid", "ask"}.issubset(names):
                raise ValueError(f"{file}: missing time/bid/ask")
            for batch in pf.iter_batches(batch_size=batch_size, columns=["time", "bid", "ask"]):
                ti = batch.schema.get_field_index("time")
                bi = batch.schema.get_field_index("bid")
                ai = batch.schema.get_field_index("ask")
                times = batch.column(ti).to_pylist()
                bids = batch.column(bi).to_pylist()
                asks = batch.column(ai).to_pylist()
                for raw_time, raw_bid, raw_ask in zip(times, bids, asks):
                    dt = as_utc(raw_time, batch.schema.field(ti).type)
                    bid, ask = float(raw_bid), float(raw_ask)
                    if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0 or ask < bid:
                        raise ValueError(f"Invalid quote encountered at {dt.isoformat()}")
                    if previous is not None and dt < previous:
                        raise ValueError(f"Out-of-order tick stream at {dt.isoformat()}")
                    previous = dt
                    day = dt.strftime("%Y-%m-%d")
                    if day not in writers:
                        path = output_root / f"XAUUSD-{day}.csv"
                        handle = path.open("w", newline="", encoding="utf-8")
                        writer = csv.writer(handle, lineterminator="\n")
                        writers[day] = (handle, writer, path, 0)
                    handle, writer, path, count = writers[day]
                    writer.writerow([
                        dt.strftime("%Y.%m.%d"),
                        dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}",
                        format(bid, ".10g"),
                        format(ask, ".10g"),
                        "0",
                        "0",
                        str(MT5_BID_ASK_FLAGS),
                    ])
                    writers[day] = (handle, writer, path, count + 1)
                    rows += 1
    finally:
        for handle, _, _, _ in writers.values():
            handle.close()
    outputs = []
    for _, _, path, count in sorted(writers.values(), key=lambda x: x[2].name):
        outputs.append({"file": path.name, "tick_count": count, "bytes": path.stat().st_size})
    result = {
        "dataset_id": report["dataset_id"],
        "symbol": "XAUUSD",
        "source_type": report["source_type"],
        "input_quality_gate": report["quality_gate"],
        "input_tick_count": report["tick_count"],
        "output_tick_count": rows,
        "first_tick_utc": report["first_tick_utc"],
        "last_tick_utc": report["last_tick_utc"],
        "mt5_flags_bid_ask": MT5_BID_ASK_FLAGS,
        "format": "Date,Time,Bid,Ask,Last,Volume,Flags; no header row",
        "outputs": outputs,
        "limitations": [
            "Preparation only; user must import into an MT5 custom symbol and validate Strategy Tester history.",
            "Dukascopy ticks are not PXBTTrading-1 broker ticks.",
            "No strategy performance is inferred from data conversion.",
        ],
    }
    (output_root / "MT5_IMPORT_MANIFEST.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Extracted daily Dukascopy Parquet directory")
    parser.add_argument("--out", required=True, help="Directory for MT5 import CSVs")
    parser.add_argument("--batch-size", type=int, default=100_000)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    result = convert(Path(args.data).resolve(), Path(args.out).resolve(), args.batch_size)
    print(json.dumps({k: result[k] for k in ("input_quality_gate", "input_tick_count", "output_tick_count", "first_tick_utc", "last_tick_utc")}, indent=2))
    print(f"Import manifest: {Path(args.out).resolve() / 'MT5_IMPORT_MANIFEST.json'}")
    return 0 if result["input_tick_count"] == result["output_tick_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
