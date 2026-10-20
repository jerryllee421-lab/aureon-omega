#!/usr/bin/env python3
"""Audit an extracted AUREON Dukascopy XAUUSD tick archive.

Reads one Parquet row-group batch at a time to keep memory bounded. This is a
data-quality gate, not an MT5 Strategy Tester and not PXBTTrading-1 broker data.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REQUIRED = {"time", "bid", "ask"}


def utc_iso(value) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def time_values(array: pa.Array) -> list[datetime]:
    """Convert common Dukascopy timestamp representations to UTC datetimes."""
    typ = array.type
    if pa.types.is_timestamp(typ):
        values = array.to_pylist()
        out = []
        for value in values:
            if value is None:
                out.append(None)
            elif value.tzinfo is None:
                out.append(value.replace(tzinfo=timezone.utc))
            else:
                out.append(value.astimezone(timezone.utc))
        return out
    if pa.types.is_string(typ) or pa.types.is_large_string(typ):
        import pandas as pd
        values = pd.to_datetime(array.to_pylist(), utc=True, errors="coerce")
        return [None if pd.isna(v) else v.to_pydatetime() for v in values]
    if pa.types.is_integer(typ) or pa.types.is_floating(typ):
        import pandas as pd
        vals = [None if v is None or not math.isfinite(float(v)) else float(v) for v in array.to_pylist()]
        finite = [v for v in vals if v is not None]
        if not finite:
            return [None] * len(vals)
        magnitude = median(abs(v) for v in finite)
        unit = "ns" if magnitude > 1e17 else "us" if magnitude > 1e14 else "ms" if magnitude > 1e11 else "s"
        converted = pd.to_datetime(vals, unit=unit, utc=True, errors="coerce")
        return [None if pd.isna(v) else v.to_pydatetime() for v in converted]
    raise ValueError(f"Unsupported time column type: {typ}")


def audit(root: Path, batch_size: int = 100_000) -> dict:
    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet tick files found under {root}")
    report = {
        "dataset_id": "AUREON_XAUUSD_DUKASCOPY_HISTORICAL_TICKS",
        "symbol": "XAUUSD",
        "source_type": "third-party Dukascopy data; NOT PXBTTrading-1 broker ticks",
        "root": str(root),
        "parquet_files": len(files),
        "tick_count": 0,
        "invalid_timestamp_count": 0,
        "nonpositive_bid_count": 0,
        "nonpositive_ask_count": 0,
        "ask_below_bid_count": 0,
        "null_quote_count": 0,
        "out_of_order_count": 0,
        "first_tick_utc": None,
        "last_tick_utc": None,
        "min_spread": None,
        "median_spread": None,
        "max_spread": None,
        "files": [],
    }
    spread_sample: list[float] = []
    for file in files:
        pf = pq.ParquetFile(file)
        names = set(pf.schema_arrow.names)
        if not REQUIRED.issubset(names):
            raise ValueError(f"{file}: missing required columns {sorted(REQUIRED - names)}")
            file_rows, file_first, file_last, prev = 0, None, None, None
        file_bad_order = 0
        for batch in pf.iter_batches(batch_size=batch_size, columns=["time", "bid", "ask"]):
            times = time_values(batch.column(batch.schema.get_field_index("time")))
            bids = batch.column(batch.schema.get_field_index("bid")).to_pylist()
            asks = batch.column(batch.schema.get_field_index("ask")).to_pylist()
            for t, bid, ask in zip(times, bids, asks):
                report["tick_count"] += 1
                file_rows += 1
                if t is None:
                    report["invalid_timestamp_count"] += 1
                else:
                    if prev is not None and t < prev:
                        report["out_of_order_count"] += 1
                        file_bad_order += 1
                    prev = t
                    if file_first is None or t < file_first:
                        file_first = t
                    if file_last is None or t > file_last:
                        file_last = t
                    if report["first_tick_utc"] is None or t < datetime.fromisoformat(report["first_tick_utc"]):
                        report["first_tick_utc"] = utc_iso(t)
                    if report["last_tick_utc"] is None or t > datetime.fromisoformat(report["last_tick_utc"]):
                        report["last_tick_utc"] = utc_iso(t)
                if bid is None or ask is None:
                    report["null_quote_count"] += 1
                    continue
                bid, ask = float(bid), float(ask)
                if not math.isfinite(bid) or bid <= 0:
                    report["nonpositive_bid_count"] += 1
                if not math.isfinite(ask) or ask <= 0:
                    report["nonpositive_ask_count"] += 1
                if math.isfinite(bid) and math.isfinite(ask):
                    if ask < bid:
                        report["ask_below_bid_count"] += 1
                    elif bid > 0:
                        if len(spread_sample) < 250_000:
                            spread_sample.append(ask - bid)
        report["files"].append({
            "path": str(file.relative_to(root)),
            "rows": file_rows,
            "coverage_start_utc": utc_iso(file_first) if file_first else None,
            "coverage_end_utc": utc_iso(file_last) if file_last else None,
            "out_of_order_count": file_bad_order,
        })
    if spread_sample:
        spread_sample.sort()
        report["min_spread"] = spread_sample[0]
        report["median_spread"] = spread_sample[len(spread_sample) // 2]
        report["max_spread"] = spread_sample[-1]
        report["spread_stats_note"] = "Spread statistics are from the first 250,000 valid spreads encountered, not a full-dataset percentile."
    errors = (
        report["tick_count"] == 0
        or report["invalid_timestamp_count"]
        or report["nonpositive_bid_count"]
        or report["nonpositive_ask_count"]
        or report["ask_below_bid_count"]
        or report["null_quote_count"]
        or report["out_of_order_count"]
    )
    report["quality_gate"] = "FAIL" if errors else "PASS"
    report["limitations"] = [
        "Third-party Dukascopy feed is not the PXBTTrading-1 broker feed.",
        "A PASS confirms basic schema and quote integrity only; it does not certify completeness, absence of gaps, or trading edge.",
        "This audit does not import ticks into MT5 Strategy Tester or claim a real-tick backtest.",
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Root directory containing extracted daily Parquet tick files")
    parser.add_argument("--out", default="tick_quality_report.json")
    parser.add_argument("--batch-size", type=int, default=100_000)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    root = Path(args.data).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    result = audit(root, args.batch_size)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "quality_gate", "tick_count", "parquet_files", "first_tick_utc", "last_tick_utc",
        "invalid_timestamp_count", "nonpositive_bid_count", "nonpositive_ask_count",
        "ask_below_bid_count", "null_quote_count", "out_of_order_count"
    )}, indent=2))
    print(f"Full report: {out}")
    return 0 if result["quality_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
