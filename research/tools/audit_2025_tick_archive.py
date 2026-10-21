#!/usr/bin/env python3
"""Audit the published monthly third-party XAUUSD tick archives for calendar 2025.

This validates the archives that exist; it does not identify them as PXBT broker ticks.
"""
from __future__ import annotations
import csv, io, json, os, re, zipfile, hashlib
from pathlib import Path
import pandas as pd

ROOT = Path("audit-input")
OUT = Path("audit-output")
OUT.mkdir(exist_ok=True)
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]
ALIASES = {
    "time": ["time", "timestamp", "datetime", "time_msc", "timestamp_ms", "date"],
    "bid": ["bid", "bid_price", "b"],
    "ask": ["ask", "ask_price", "a"],
}
def norm(s): return re.sub(r"[^a-z0-9]+", "", str(s).lower())
def find_col(columns, names):
    cmap = {norm(c): c for c in columns}
    for n in names:
        if norm(n) in cmap: return cmap[norm(n)]
    for c in columns:
        if any(norm(n) in norm(c) for n in names): return c
    return None
def load_member(zf, name):
    raw = zf.read(name)
    low = name.lower()
    if low.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(raw))
    if low.endswith((".csv", ".txt")):
        return pd.read_csv(io.BytesIO(raw), low_memory=False)
    return None
def audit_frame(df, archive, member):
    cols = list(df.columns)
    tc, bc, ac = (find_col(cols, ALIASES[k]) for k in ("time", "bid", "ask"))
    row = {"archive": archive, "member": member, "rows": int(len(df)),
           "columns": [str(c) for c in cols], "timestamp_column": str(tc) if tc is not None else None,
           "bid_column": str(bc) if bc is not None else None, "ask_column": str(ac) if ac is not None else None}
    if tc is None or bc is None or ac is None:
        row.update({"schema_status": "UNRECOGNIZED", "error": "Could not identify timestamp, bid and ask columns"})
        return row
    t = df[tc]
    if pd.api.types.is_numeric_dtype(t):
        # Infer common epoch units from median magnitude.
        med = pd.to_numeric(t, errors="coerce").dropna().median()
        unit = "ms" if med > 1e11 else ("us" if med > 1e14 else "s")
        ts = pd.to_datetime(t, unit=unit, utc=True, errors="coerce")
    else:
        ts = pd.to_datetime(t, utc=True, errors="coerce")
    bid = pd.to_numeric(df[bc], errors="coerce")
    ask = pd.to_numeric(df[ac], errors="coerce")
    spread = ask - bid
    valid = ts.notna() & bid.notna() & ask.notna()
    row.update({
        "schema_status": "OK",
        "valid_quote_rows": int(valid.sum()),
        "invalid_quote_rows": int((~valid).sum()),
        "min_timestamp_utc": ts.min().isoformat() if ts.notna().any() else None,
        "max_timestamp_utc": ts.max().isoformat() if ts.notna().any() else None,
        "min_bid": float(bid.min()) if bid.notna().any() else None,
        "max_ask": float(ask.max()) if ask.notna().any() else None,
        "negative_spread_rows": int((spread < 0).sum()),
        "zero_spread_rows": int((spread == 0).sum()),
        "max_spread": float(spread.max()) if spread.notna().any() else None,
        "duplicate_quote_rows": int(df.duplicated(subset=[tc, bc, ac]).sum()),
        "timestamp_monotonic": bool(ts.dropna().is_monotonic_increasing),
        "time_unit_inferred": unit if pd.api.types.is_numeric_dtype(t) else "parsed datetime",
    })
    return row

reports = []
archive_summaries = []
errors = []
for month in MONTHS:
    path = ROOT / f"xauusd-ticks-{month}.zip"
    if not path.exists():
        errors.append(f"MISSING_ARCHIVE:{path.name}")
        continue
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            members = [n for n in zf.namelist() if not n.endswith("/")]
            archive_summaries.append({"archive": path.name, "sha256": sha, "compressed_bytes": path.stat().st_size,
                                      "members": len(members), "zip_integrity": "OK" if bad is None else f"BAD:{bad}",
                                      "member_names": members[:100]})
            if bad:
                errors.append(f"ZIP_CORRUPT:{path.name}:{bad}")
                continue
            found = 0
            for name in members:
                low = name.lower()
                if low.endswith((".parquet", ".csv", ".txt")):
                    try:
                        frame = load_member(zf, name)
                        if frame is not None:
                            reports.append(audit_frame(frame, path.name, name))
                            found += 1
                    except Exception as e:
                        errors.append(f"READ_ERROR:{path.name}:{name}:{type(e).__name__}:{e}")
                elif low.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(io.BytesIO(zf.read(name))) as nested:
                            for n2 in nested.namelist():
                                if n2.lower().endswith((".parquet", ".csv", ".txt")):
                                    frame = load_member(nested, n2)
                                    if frame is not None:
                                        reports.append(audit_frame(frame, path.name, name + "::" + n2))
                                        found += 1
                    except Exception as e:
                        errors.append(f"NESTED_READ_ERROR:{path.name}:{name}:{type(e).__name__}:{e}")
            if found == 0:
                errors.append(f"NO_SUPPORTED_TICK_TABLE:{path.name}")
    except Exception as e:
        errors.append(f"ZIP_OPEN_ERROR:{path.name}:{type(e).__name__}:{e}")

(OUT / "archive-integrity.json").write_text(json.dumps(archive_summaries, indent=2), encoding="utf-8")
(OUT / "table-audit.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
(OUT / "errors.txt").write_text("\n".join(errors) + ("\n" if errors else "No structural errors detected.\n"), encoding="utf-8")
with (OUT / "table-audit.csv").open("w", newline="", encoding="utf-8") as f:
    if reports:
        keys = sorted({k for r in reports for k in r})
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in reports: w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k,v in r.items()})
valid = [r for r in reports if r.get("schema_status") == "OK"]
summary = {
    "scope": "Published third-party Dukascopy XAUUSD archive; not PrimeXBT-native tick data",
    "expected_months": MONTHS,
    "archives_found": len(archive_summaries),
    "tables_found": len(reports),
    "recognized_tables": len(valid),
    "total_rows": sum(r.get("rows", 0) for r in valid),
    "valid_quote_rows": sum(r.get("valid_quote_rows", 0) for r in valid),
    "invalid_quote_rows": sum(r.get("invalid_quote_rows", 0) for r in valid),
    "negative_spread_rows": sum(r.get("negative_spread_rows", 0) for r in valid),
    "duplicate_quote_rows": sum(r.get("duplicate_quote_rows", 0) for r in valid),
    "errors": errors,
    "qualification": "AUDIT_ONLY_NOT_BROKER_CERTIFIED" if not errors and len(archive_summaries) == 12 and valid else "BLOCKED_INCOMPLETE_OR_UNRECOGNIZED",
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
if errors or len(archive_summaries) != 12 or not valid:
    raise SystemExit(2)
