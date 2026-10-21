#!/usr/bin/env python3
"""Recover missing 2025-01-01..19 XAUUSD ticks from public Dukascopy hourly BI5.

Third-party data only. Does not imply PrimeXBT-native equivalence.
Raw BI5 files are not committed; validated parquet and manifest are workflow artifacts.
"""
from __future__ import annotations
import hashlib, json, lzma, struct, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2025, 1, 20, tzinfo=timezone.utc)
BASE = "https://datafeed.dukascopy.com/datafeed/XAUUSD"
OUT = Path("recovery-output")
OUT.mkdir(exist_ok=True)
REC = struct.Struct(">IIIff")
PRICE_SCALE = 1000  # XAUUSD point scaling; validate against existing dataset before merging
rows = []
hourly = []
errors = []
total_bytes = 0

def fetch(url: str):
    global total_bytes
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AUREON-research-data-audit/1.0"})
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read()
                total_bytes += len(body)
                return "OK", body, response.status
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "MISSING", b"", 404
            if e.code not in (408, 425, 429, 500, 502, 503, 504):
                return "ERROR", b"", e.code
            time.sleep(min(2 ** attempt, 12))
        except Exception:
            time.sleep(min(2 ** attempt, 12))
    return "ERROR", b"", None

day = START
while day < END:
    day_rows = 0
    day_hours_ok = 0
    day_hours_empty = 0
    day_hours_missing = 0
    for hour in range(24):
        url = f"{BASE}/{day.year}/{day.month-1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5"
        status, payload, code = fetch(url)
        count = 0
        detail = ""
        if status == "OK" and payload:
            try:
                raw = lzma.decompress(payload)
                if len(raw) % REC.size:
                    raise ValueError(f"decompressed bytes {len(raw)} not divisible by {REC.size}")
                base_ms = int(datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc).timestamp() * 1000)
                for ms, ask_i, bid_i, ask_vol, bid_vol in REC.iter_unpack(raw):
                    ask = ask_i / PRICE_SCALE
                    bid = bid_i / PRICE_SCALE
                    ts = base_ms + ms
                    if ms >= 3_600_000:
                        raise ValueError(f"hour offset outside hour: {ms}")
                    rows.append((ts, bid, ask, ask_vol, bid_vol))
                    count += 1
                day_hours_ok += 1
            except Exception as e:
                errors.append({"date": day.strftime("%Y-%m-%d"), "hour": hour, "url": url, "error": f"{type(e).__name__}: {e}"})
                detail = f"DECODE_ERROR:{type(e).__name__}"
        elif status == "OK":
            day_hours_empty += 1
            detail = "EMPTY"
        elif status == "MISSING":
            day_hours_missing += 1
            detail = "HTTP_404_NO_DATA"
        else:
            errors.append({"date": day.strftime("%Y-%m-%d"), "hour": hour, "url": url, "error": f"HTTP_OR_FETCH_ERROR:{code}"})
            detail = f"FETCH_ERROR:{code}"
        day_rows += count
        hourly.append({"date": day.strftime("%Y-%m-%d"), "hour_utc": hour, "status": detail or "OK", "ticks": count, "http_status": code, "bytes": len(payload)})
        time.sleep(0.08)
    print(f"{day:%Y-%m-%d}: ticks={day_rows:,}; hours_with_data={day_hours_ok}; empty={day_hours_empty}; missing={day_hours_missing}")
    day += timedelta(days=1)

df = pd.DataFrame(rows, columns=["timestamp_ms_utc", "bid", "ask", "bid_volume", "ask_volume"])
if not df.empty:
    df["timestamp"] = pd.to_datetime(df["timestamp_ms_utc"], unit="ms", utc=True)
    df = df.sort_values("timestamp_ms_utc", kind="stable").reset_index(drop=True)
    df["spread"] = df["ask"] - df["bid"]
    invalid = int((~df["timestamp"].notna() | (df["bid"] <= 0) | (df["ask"] <= 0) | df["bid"].isna() | df["ask"].isna()).sum())
    negative_spread = int((df["spread"] < 0).sum())
    duplicate_quotes = int(df.duplicated(subset=["timestamp_ms_utc", "bid", "ask"]).sum())
    non_monotonic = not df["timestamp_ms_utc"].is_monotonic_increasing
    first_ts = df["timestamp"].min().isoformat()
    last_ts = df["timestamp"].max().isoformat()
    min_bid, max_ask = float(df["bid"].min()), float(df["ask"].max())
    max_spread = float(df["spread"].max())
    df.to_parquet(OUT / "xauusd-dukascopy-ticks-2025-01-01-to-2025-01-19.parquet", index=False, compression="zstd")
else:
    invalid = negative_spread = duplicate_quotes = 0
    non_monotonic = True
    first_ts = last_ts = None
    min_bid = max_ask = max_spread = None

daily = []
for day_str in [(START + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((END-START).days)]:
    d = [x for x in hourly if x["date"] == day_str]
    daily.append({"date": day_str, "ticks": sum(x["ticks"] for x in d),
                  "hours_with_ticks": sum(x["ticks"] > 0 for x in d),
                  "empty_or_missing_hours": sum(x["ticks"] == 0 for x in d)})
(OUT / "hourly-fetch-inventory.json").write_text(json.dumps(hourly, indent=2), encoding="utf-8")
(OUT / "daily-coverage.json").write_text(json.dumps(daily, indent=2), encoding="utf-8")
manifest = {
    "source": "Dukascopy public historical datafeed; third-party, not PrimeXBT-native",
    "symbol": "XAUUSD",
    "requested_utc_range": {"start_inclusive": START.isoformat(), "end_exclusive": END.isoformat()},
    "price_scale": PRICE_SCALE,
    "record_format": "LZMA BI5; big-endian >IIIff; hour-relative milliseconds, ask integer, bid integer, ask volume, bid volume",
    "hourly_urls_requested": len(hourly),
    "hours_with_data": sum(x["ticks"] > 0 for x in hourly),
    "hours_empty_or_missing": sum(x["ticks"] == 0 for x in hourly),
    "ticks": len(df),
    "first_tick_utc": first_ts,
    "last_tick_utc": last_ts,
    "min_bid": min_bid, "max_ask": max_ask, "max_spread": max_spread,
    "invalid_quote_rows": invalid,
    "negative_spread_rows": negative_spread,
    "duplicate_quote_rows": duplicate_quotes,
    "timestamps_monotonic_after_sort": not non_monotonic,
    "downloaded_bytes": total_bytes,
    "fetch_decode_errors": errors,
    "sha256_parquet": hashlib.sha256((OUT / "xauusd-dukascopy-ticks-2025-01-01-to-2025-01-19.parquet").read_bytes()).hexdigest() if not df.empty else None,
    "status": "RECOVERED_RESEARCH_DATA_ONLY" if len(df) > 0 and not errors and invalid == 0 and negative_spread == 0 and duplicate_quotes == 0 and not non_monotonic else "BLOCKED_VALIDATION_FAILURE",
    "merge_gate": "Do not merge until price scale, timestamp semantics, source overlap and boundary duplicates are checked against existing archive."
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
if not len(df) or errors or invalid or negative_spread or duplicate_quotes or non_monotonic:
    raise SystemExit(2)
