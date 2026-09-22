from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import lzma
import struct
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = "https://datafeed.dukascopy.com/datafeed"
REC = struct.Struct(">IIIIIf")  # seconds, open, close, low, high, volume
PRICE_SCALE = {"XAUUSD": 1000}

@dataclass(frozen=True)
class DayResult:
    day: str
    side: str
    rows: int
    status: str
    path: str | None = None


def days_between(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def url_for(symbol: str, d: date, side: str) -> str:
    return f"{BASE}/{symbol}/{d.year:04d}/{d.month-1:02d}/{d.day:02d}/{side}_candles_min_1.bi5"


def raw_path(cache: Path, symbol: str, d: date, side: str) -> Path:
    return cache / symbol / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}_{side}.bi5"


def fetch_one(symbol: str, d: date, side: str, cache: Path, retries: int = 6) -> DayResult:
    path = raw_path(cache, symbol, d, side)
    if path.exists() and path.stat().st_size > 0:
        try:
            rows = len(lzma.decompress(path.read_bytes())) // REC.size
            return DayResult(d.isoformat(), side, rows, "cached", str(path))
        except Exception:
            path.unlink(missing_ok=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    url = url_for(symbol, d, side)
    last = ""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=45, headers={"User-Agent": "AUREON-GOLD-RESEARCH/1.0"})
            if r.status_code == 200 and r.content:
                # Validate before caching.
                decoded = lzma.decompress(r.content)
                if len(decoded) % REC.size:
                    raise ValueError(f"decoded byte count {len(decoded)} not divisible by {REC.size}")
                path.write_bytes(r.content)
                return DayResult(d.isoformat(), side, len(decoded)//REC.size, "downloaded", str(path))
            if r.status_code in (404, 410) or (r.status_code == 200 and not r.content):
                return DayResult(d.isoformat(), side, 0, f"empty_{r.status_code}")
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(min(20, 1.5 * (2**attempt)))
    return DayResult(d.isoformat(), side, 0, f"failed:{last}")


def decode_day(path: Path, d: date, side: str, scale: int) -> pd.DataFrame:
    raw = lzma.decompress(path.read_bytes())
    records = []
    midnight = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    for off in range(0, len(raw), REC.size):
        sec, op, cl, lo, hi, vol = REC.unpack(raw[off:off+REC.size])
        if op == 0 or cl == 0 or lo == 0 or hi == 0:
            continue
        o, c, l, h = op/scale, cl/scale, lo/scale, hi/scale
        if not (h >= max(o, c) and l <= min(o, c) and h >= l):
            continue
        records.append((midnight + timedelta(seconds=int(sec)), o, h, l, c, float(vol)))
    return pd.DataFrame(records, columns=["time", f"{side.lower()}_open", f"{side.lower()}_high", f"{side.lower()}_low", f"{side.lower()}_close", f"{side.lower()}_volume"])


def build_month(cache: Path, symbol: str, year: int, month: int, output: Path, scale: int) -> int:
    frames = []
    d = date(year, month, 1)
    next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    while d < next_month:
        bp = raw_path(cache, symbol, d, "BID")
        ap = raw_path(cache, symbol, d, "ASK")
        if bp.exists() and ap.exists() and bp.stat().st_size and ap.stat().st_size:
            try:
                bid = decode_day(bp, d, "BID", scale)
                ask = decode_day(ap, d, "ASK", scale)
                if not bid.empty and not ask.empty:
                    merged = bid.merge(ask, on="time", how="inner", validate="one_to_one")
                    frames.append(merged)
            except Exception as e:
                print(f"WARN decode {d}: {e}")
        d += timedelta(days=1)
    if not frames:
        return 0
    df = pd.concat(frames, ignore_index=True).sort_values("time").drop_duplicates("time")
    df["spread_open"] = df["ask_open"] - df["bid_open"]
    df["spread_close"] = df["ask_close"] - df["bid_close"]
    df["mid_open"] = (df["ask_open"] + df["bid_open"]) / 2
    df["mid_high"] = (df["ask_high"] + df["bid_high"]) / 2
    df["mid_low"] = (df["ask_low"] + df["bid_low"]) / 2
    df["mid_close"] = (df["ask_close"] + df["bid_close"]) / 2
    out = output / symbol / "M1" / f"year={year:04d}" / f"month={month:02d}" / "bars.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False, compression="zstd")
    return len(df)


def sha256_tree(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*.parquet")):
        h.update(p.relative_to(path).as_posix().encode())
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--cache", default=".cache/dukascopy")
    ap.add_argument("--output", default="research_data")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    scale = PRICE_SCALE.get(symbol)
    if not scale:
        raise SystemExit(f"No verified price scale configured for {symbol}; refusing to guess.")
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end before start")
    cache, output = Path(args.cache), Path(args.output)
    tasks = [(d, s) for d in days_between(start, end) for s in ("BID", "ASK")]
    failures = []
    with cf.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 20))) as ex:
        futs = {ex.submit(fetch_one, symbol, d, side, cache): (d, side) for d, side in tasks}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r = fut.result()
            if r.status.startswith("failed"):
                failures.append(r.__dict__)
            if i % 100 == 0 or i == len(futs):
                print(f"fetch {i}/{len(futs)} failures={len(failures)}")

    months = sorted({(d.year, d.month) for d in days_between(start, end)})
    total = 0
    for y, m in months:
        n = build_month(cache, symbol, y, m, output, scale)
        total += n
        print(f"built {y}-{m:02d}: {n:,} M1 rows")

    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": "DUKASCOPY_EXTERNAL",
        "symbol": symbol,
        "start_requested": start.isoformat(),
        "end_requested": end.isoformat(),
        "m1_rows": total,
        "failed_requests": failures,
        "dataset_sha256": sha256_tree(output / symbol / "M1"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    import json
    (output / symbol / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if failures:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
