#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPO = "kevingtlin/Market-Data-Lab"
DEFAULT_COMMIT = "922f83a60cc574e7395fb27397077288055a1ef6"


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AUREON-MT5-CI/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def parse_csv(raw: bytes) -> dict[int, dict[str, float]]:
    text = raw.decode("utf-8-sig")
    out: dict[int, dict[str, float]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        ts = int(row["timestamp"])
        out[ts] = {
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--month", type=int, default=8)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--commit", default=DEFAULT_COMMIT)
    ap.add_argument("--output", default="mt5_ci_data/aureon_gold_m1.csv")
    ap.add_argument("--manifest", default="mt5_ci_data/source_manifest.json")
    ap.add_argument("--point", type=float, default=0.001)
    args = ap.parse_args()

    stem = f"{args.year:04d}_{args.month:02d}"
    base = f"https://raw.githubusercontent.com/{args.repo}/{args.commit}/xauusd"
    bid_url = f"{base}/bid/m1/xauusd_bid_m1_{stem}.csv"
    ask_url = f"{base}/ask/m1/xauusd_ask_m1_{stem}.csv"

    bid_raw = fetch_bytes(bid_url)
    ask_raw = fetch_bytes(ask_url)

    bid = parse_csv(bid_raw)
    ask = parse_csv(ask_raw)
    common = sorted(set(bid) & set(ask))
    if not common:
        raise SystemExit("No overlapping bid/ask M1 rows found")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    first_dt = None
    last_dt = None
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "time",
            "bid_open", "bid_high", "bid_low", "bid_close",
            "ask_open", "ask_high", "ask_low", "ask_close",
            "spread_points"
        ])
        for ts in common:
            b = bid[ts]
            a = ask[ts]
            dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
            first_dt = first_dt or dt
            last_dt = dt
            spread_points = max(0, int(round((a["close"] - b["close"]) / args.point)))
            w.writerow([
                dt.strftime("%Y.%m.%d %H:%M:%S"),
                f"{b['open']:.6f}", f"{b['high']:.6f}", f"{b['low']:.6f}", f"{b['close']:.6f}",
                f"{a['open']:.6f}", f"{a['high']:.6f}", f"{a['low']:.6f}", f"{a['close']:.6f}",
                spread_points,
            ])

    manifest = {
        "source": "DUKASCOPY_EXTERNAL",
        "transport": "PINNED_GITHUB_MIRROR",
        "repo": args.repo,
        "commit": args.commit,
        "year": args.year,
        "month": args.month,
        "rows": len(common),
        "first_utc": first_dt.isoformat() if first_dt else None,
        "last_utc": last_dt.isoformat() if last_dt else None,
        "bid_url": bid_url,
        "ask_url": ask_url,
        "bid_sha256": hashlib.sha256(bid_raw).hexdigest(),
        "ask_sha256": hashlib.sha256(ask_raw).hexdigest(),
        "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "volume_semantics": "not provided by source; MT5 loader uses modeling tick_volume=4 only for 1-minute-OHLC generation and does not represent market volume",
        "price_semantics": "custom symbol bars use bid OHLC; minute spread_points derived from ask_close-bid_close",
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
