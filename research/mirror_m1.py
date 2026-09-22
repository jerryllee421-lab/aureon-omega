from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DEFAULT_REPO = "kevingtlin/Market-Data-Lab"
DEFAULT_COMMIT = "922f83a60cc574e7395fb27397077288055a1ef6"
DEFAULT_LATEST = date(2026, 8, 20)
REQUIRED = ["timestamp", "open", "high", "low", "close"]


def month_iter(start: date, end: date):
    d = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    while d <= stop:
        yield d.year, d.month
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_csv(repo: str, commit: str, side: str, year: int, month: int, retries: int = 4):
    path = f"xauusd/{side}/m1/xauusd_{side}_m1_{year:04d}_{month:02d}.csv"
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=(10, 90), headers={"User-Agent": "AUREON-GOLD-RESEARCH/1.1"})
            if r.status_code == 200 and r.content:
                frame = pd.read_csv(io.BytesIO(r.content))
                missing = [c for c in REQUIRED if c not in frame.columns]
                if missing:
                    raise ValueError(f"{path}: missing columns {missing}")
                return frame[REQUIRED].copy(), {
                    "path": path,
                    "url": url,
                    "sha256": sha256_bytes(r.content),
                    "bytes": len(r.content),
                    "rows": len(frame),
                }
            last = f"HTTP {r.status_code}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(min(10, 1.5 * (2 ** attempt)))
    raise RuntimeError(f"Unable to fetch {path}: {last}")


def normalize(frame: pd.DataFrame, side: str) -> pd.DataFrame:
    x = frame.copy()
    x["time"] = pd.to_datetime(x["timestamp"], unit="ms", utc=True)
    x = x.drop(columns=["timestamp"])
    x = x.rename(columns={c: f"{side}_{c}" for c in ("open", "high", "low", "close")})
    for c in ("open", "high", "low", "close"):
        x[f"{side}_{c}"] = pd.to_numeric(x[f"{side}_{c}"], errors="coerce")
    return x.dropna().sort_values("time").drop_duplicates("time")


def build_month(bid: pd.DataFrame, ask: pd.DataFrame) -> pd.DataFrame:
    x = normalize(bid, "bid").merge(normalize(ask, "ask"), on="time", how="inner", validate="one_to_one")
    for c in ("open", "high", "low", "close"):
        x[f"mid_{c}"] = (x[f"bid_{c}"] + x[f"ask_{c}"]) / 2.0
    x["spread_open"] = x["ask_open"] - x["bid_open"]
    x["spread_close"] = x["ask_close"] - x["bid_close"]
    return x.sort_values("time")


def tree_hash(files: list[Path], root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(files):
        h.update(p.relative_to(root).as_posix().encode())
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=DEFAULT_LATEST.isoformat())
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--commit", default=DEFAULT_COMMIT)
    ap.add_argument("--output", default="research_data")
    args = ap.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end > DEFAULT_LATEST and args.commit == DEFAULT_COMMIT:
        raise SystemExit(f"Pinned mirror only verified through {DEFAULT_LATEST.isoformat()}; requested {end.isoformat()}")
    if start > end:
        raise SystemExit("start must be <= end")

    root = Path(args.output)
    outdir = root / "XAUUSD" / "M1"
    outdir.mkdir(parents=True, exist_ok=True)
    evidence = []
    parquet_files = []
    actual_first = None
    actual_last = None
    total_rows = 0

    start_ts = pd.Timestamp(start, tz="UTC")
    end_exclusive = pd.Timestamp(end + timedelta(days=1), tz="UTC")

    for year, month in month_iter(start, end):
        print(f"fetch {year:04d}-{month:02d}", flush=True)
        bid, be = fetch_csv(args.repo, args.commit, "bid", year, month)
        ask, ae = fetch_csv(args.repo, args.commit, "ask", year, month)
        merged = build_month(bid, ask)
        merged = merged[(merged["time"] >= start_ts) & (merged["time"] < end_exclusive)]
        evidence.extend([be, ae])
        if merged.empty:
            continue
        out = outdir / f"year={year:04d}" / f"month={month:02d}" / "bars.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(out, index=False, compression="zstd")
        parquet_files.append(out)
        total_rows += len(merged)
        first = merged["time"].iloc[0]
        last = merged["time"].iloc[-1]
        actual_first = first if actual_first is None or first < actual_first else actual_first
        actual_last = last if actual_last is None or last > actual_last else actual_last
        print(f"  rows={len(merged):,} first={first} last={last}", flush=True)

    if not parquet_files:
        raise SystemExit("No XAUUSD M1 rows were produced")

    manifest = {
        "source": "DUKASCOPY_EXTERNAL",
        "transport": "PINNED_GITHUB_MIRROR",
        "mirror_repo": args.repo,
        "mirror_commit": args.commit,
        "mirror_verified_latest_date": DEFAULT_LATEST.isoformat(),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "actual_first": actual_first.isoformat() if actual_first is not None else None,
        "actual_last": actual_last.isoformat() if actual_last is not None else None,
        "m1_rows": total_rows,
        "dataset_sha256": tree_hash(parquet_files, root),
        "source_files": evidence,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (root / "XAUUSD" / "download_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("source", "transport", "mirror_commit", "actual_first", "actual_last", "m1_rows", "dataset_sha256")}, indent=2))


if __name__ == "__main__":
    main()
