#!/usr/bin/env python3
"""Audit the published monthly third-party XAUUSD tick archives for calendar 2025.

This validates the archives that exist; it does not identify them as PXBT broker ticks.
"""
from __future__ import annotations
import csv, io, json, os, re, zipfile, hashlib
from pathlib import Path
import pandas as pd
from research.tools.timestamp_units import infer_epoch_unit

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
        unit = infer_epoch_unit(float(abs(med)))
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
file_date_inventory = []
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
                            dm = re.search(r"(20\d{2}-\d{2}-\d{2})", name)
                            if dm:
                                file_date_inventory.append({"date": dm.group(1), "archive": path.name, "rows": int(len(frame)), "member": name})
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
all_dates = sorted({x["date"] for x in file_date_inventory})
calendar_dates = pd.date_range("2025-01-01", "2025-12-31", freq="D").strftime("%Y-%m-%d").tolist()
calendar_inventory = [x for x in file_date_inventory if x["date"].startswith("2025-")]
calendar_nonempty = sorted({x["date"] for x in calendar_inventory if x["rows"] > 0})
calendar_empty = sorted({x["date"] for x in calendar_inventory if x["rows"] == 0})
calendar_missing_files = sorted(set(calendar_dates) - {x["date"] for x in calendar_inventory})
calendar_missing_quote_dates = sorted(set(calendar_dates) - set(calendar_nonempty))
archive_name_mismatch = [x["archive"] for x in archive_summaries if not re.fullmatch(r"xauusd-ticks-2025-(0[1-9]|1[0-2])\.zip", x["archive"])]
archive_naming_note = "Archive filenames are monthly labels only; verify member timestamp ranges because the published data windows may roll across month boundaries."
coverage = {
    "calendar_year": "2025",
    "expected_calendar_days": len(calendar_dates),
    "daily_files_for_2025": len(calendar_inventory),
    "dates_with_quotes": len(calendar_nonempty),
    "empty_daily_files": len(calendar_empty),
    "missing_daily_files": calendar_missing_files,
    "dates_without_quotes_including_expected_market_closures": calendar_missing_quote_dates,
    "first_date_with_quotes": min(calendar_nonempty) if calendar_nonempty else None,
    "last_date_with_quotes": max(calendar_nonempty) if calendar_nonempty else None,
    "complete_calendar_file_coverage": not calendar_missing_files,
    "archive_filenames_match_monthly_label_pattern": not archive_name_mismatch,
    "archive_filenames_not_matching_monthly_label_pattern": archive_name_mismatch,
    "archive_naming_note": archive_naming_note,
    "note": "Empty weekend/market-closure files are not automatically data defects; dates without files are reported separately."
}
(OUT / "calendar-coverage.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")
(OUT / "daily-file-inventory.json").write_text(json.dumps(file_date_inventory, indent=2), encoding="utf-8")
summary = {
    "scope": "Published third-party Dukascopy XAUUSD archive; not PrimeXBT-native tick data",
    "calendar_coverage": coverage,
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
    "qualification": "AUDIT_ONLY_NOT_BROKER_CERTIFIED" if not errors and len(archive_summaries) == 12 and valid and coverage["complete_calendar_file_coverage"] else "BLOCKED_INCOMPLETE_COVERAGE_OR_UNRECOGNIZED",
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
if errors or len(archive_summaries) != 12 or not valid or not coverage["complete_calendar_file_coverage"]:
    raise SystemExit(2)
