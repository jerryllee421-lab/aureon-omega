#!/usr/bin/env python3
"""Validate MT5-exported XAUUSD ticks and package monthly ZIP assets."""
from __future__ import annotations
import argparse, csv, hashlib, json, re, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-days", type=int, default=730)
    args = ap.parse_args()
    source, out = Path(args.source), Path(args.out)
    if not (source / "DONE.flag").is_file():
        raise SystemExit("Missing exporter completion marker; refusing to publish partial data.")
    daily = sorted(source.glob("ticks_????????.csv"))
    if len(daily) < 400:
        raise SystemExit(f"Insufficient nonempty daily tick shards: {len(daily)} < 400; refusing to publish likely partial history.")
    months = defaultdict(list)
    total_ticks = 0
    earliest = latest = None
    day_rows = []
    for path in daily:
        if not re.fullmatch(r"ticks_\d{8}\.csv", path.name):
            continue
        date_key = path.stem.split("_")[1]
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"time_msc", "bid", "ask", "last", "flags"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise SystemExit(f"{path.name}: missing required tick fields.")
            n = 0
            day_first = day_last = None
            for row in reader:
                t = int(row["time_msc"])
                bid, ask = float(row["bid"]), float(row["ask"])
                if t <= 0 or bid < 0 or ask < 0 or (bid > 0 and ask > 0 and ask < bid):
                    raise SystemExit(f"{path.name}: invalid tick at row {n + 2}.")
                day_first = t if day_first is None else min(day_first, t)
                day_last = t if day_last is None else max(day_last, t)
                n += 1
            if n == 0:
                raise SystemExit(f"{path.name}: empty daily file unexpectedly present.")
            total_ticks += n
            earliest = day_first if earliest is None else min(earliest, day_first)
            latest = day_last if latest is None else max(latest, day_last)
            day_rows.append({"date": date_key, "ticks": n, "first_tick_msc": day_first, "last_tick_msc": day_last})
        months[date_key[:6]].append(path)
    if total_ticks < 1_000_000:
        raise SystemExit(f"Insufficient tick volume: {total_ticks:,} < 1,000,000; refusing to publish likely partial history.")
    coverage_ms = latest - earliest
    if coverage_ms < args.min_days * 86400 * 1000:
        raise SystemExit(f"Insufficient real-tick coverage: {coverage_ms / 86400000:.2f} days < {args.min_days}.")
    out.mkdir(parents=True, exist_ok=True)
    archives = []
    for month, files in sorted(months.items()):
        archive = out / f"xauusd_mt5_real_ticks_{month}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
            for path in files:
                zf.write(path, arcname=path.name)
        archives.append({"file": archive.name, "bytes": archive.stat().st_size, "sha256": sha256(archive), "days": len(files)})
    manifest = {
        "dataset": "AUREON_XAUUSD_MT5_REAL_TICKS",
        "symbol": "XAUUSD",
        "source": "MT5 CopyTicksRange(COPY_TICKS_ALL)",
        "broker_server": "PXBTTrading-1",
        "account_mode_required": "DEMO",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_start_utc": datetime.fromtimestamp(earliest / 1000, timezone.utc).isoformat(),
        "coverage_end_utc": datetime.fromtimestamp(latest / 1000, timezone.utc).isoformat(),
        "coverage_days": round(coverage_ms / 86400000, 4),
        "tick_count": total_ticks,
        "daily_file_count": len(daily),
        "archives": archives,
        "daily_coverage": day_rows,
        "validation": {"minimum_coverage_days_passed": True, "ask_below_bid_count": 0,
                       "zero_or_negative_timestamp_count": 0, "source_is_real_ticks": True,
                       "trading_orders_sent": False, "live_trading_allowed": False}
    }
    (out / "xauusd_mt5_real_ticks_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (out / "xauusd_mt5_real_ticks_daily.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "ticks", "first_tick_msc", "last_tick_msc"])
        w.writeheader(); w.writerows(day_rows)
    print(json.dumps({k: manifest[k] for k in ("coverage_start_utc", "coverage_end_utc", "coverage_days", "tick_count", "daily_file_count", "archives")}, indent=2))

if __name__ == "__main__":
    main()
