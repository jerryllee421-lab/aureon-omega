#!/usr/bin/env python3
"""Coverage and intraday-gap diagnostics for extracted XAUUSD Parquet tick files.

Reports coverage evidence without assuming that every calendar day or every minute
must contain ticks. Third-party feed diagnostics only; not broker-feed certification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from research.evolution.audit_dukascopy_tick_archive import time_values


def audit_coverage(root: Path, gap_seconds: float = 60.0) -> dict:
    if gap_seconds <= 0:
        raise ValueError("gap_seconds must be positive")
    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files found under {root}")
    days = {}
    total = 0
    for path in files:
        pf = pq.ParquetFile(path)
        if not {"time", "bid", "ask"}.issubset(pf.schema_arrow.names):
            raise ValueError(f"{path}: missing time/bid/ask columns")
        times = []
        rows = 0
        for batch in pf.iter_batches(batch_size=100_000, columns=["time"]):
            values = time_values(batch.column(0))
            times.extend(v for v in values if v is not None)
            rows += len(values)
        times.sort()
        total += rows
        by_day = {}
        for ts in times:
            day = ts.date().isoformat()
            item = by_day.setdefault(day, {"timestamps": [], "tick_count": 0})
            item["timestamps"].append(ts)
            item["tick_count"] += 1
        for day, item in by_day.items():
            seq = item["timestamps"]
            gaps = [(b-a).total_seconds() for a, b in zip(seq, seq[1:])]
            record = days.setdefault(day, {"tick_count": 0, "files": [], "first_tick_utc": None,
                                           "last_tick_utc": None, "gaps_over_threshold": 0,
                                           "largest_gap_seconds": 0.0})
            record["tick_count"] += item["tick_count"]
            record["files"].append(str(path.relative_to(root)))
            first, last = seq[0].isoformat(), seq[-1].isoformat()
            if record["first_tick_utc"] is None or first < record["first_tick_utc"]:
                record["first_tick_utc"] = first
            if record["last_tick_utc"] is None or last > record["last_tick_utc"]:
                record["last_tick_utc"] = last
            record["gaps_over_threshold"] += sum(g > gap_seconds for g in gaps)
            record["largest_gap_seconds"] = max(record["largest_gap_seconds"], max(gaps, default=0.0))
    return {
        "dataset": "AUREON_XAUUSD_TICK_COVERAGE_DIAGNOSTICS",
        "source_type": "file-level timestamps; feed is not certified as PXBTTrading-1 native history",
        "root": str(root),
        "file_count": len(files),
        "tick_count": total,
        "gap_threshold_seconds": gap_seconds,
        "observed_calendar_days": len(days),
        "days": {k: days[k] for k in sorted(days)},
        "interpretation": "Large gaps require review, not automatic rejection: market closures, provider outages, and sparse quoting can differ.",
        "quality_gate": "REVIEW_REQUIRED" if any(v["gaps_over_threshold"] or v["largest_gap_seconds"] > gap_seconds for v in days.values()) else "NO_LARGE_INTRADAY_GAPS_DETECTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Root directory containing Parquet tick files")
    parser.add_argument("--out", default="tick_coverage_report.json")
    parser.add_argument("--gap-seconds", type=float, default=60.0)
    args = parser.parse_args()
    result = audit_coverage(Path(args.data).resolve(), args.gap_seconds)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("quality_gate", "file_count", "tick_count", "observed_calendar_days", "gap_threshold_seconds")}, indent=2))
    print(f"Full report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
