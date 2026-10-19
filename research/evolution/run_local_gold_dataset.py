"""Prepare a bounded canonical XAUUSD parquet set and run the research-only lab."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

TF_ORDER = ("M5", "M15", "M30", "H1", "M1", "H4", "D1")
TIME_NAMES = ("time", "time_utc", "timestamp", "datetime", "date")

def timeframe(path: Path):
    for tf in TF_ORDER:
        if re.search(rf"(^|[^A-Z0-9]){tf}([^A-Z0-9]|$)", path.name.upper()):
            return tf
    return None

def source_anchor(file: Path, root: Path):
    ancestors = [p for p in file.parents if p == root or root in p.parents]
    canonical = [p for p in ancestors if p.name.lower() in {"canonical", "gold_canonical"}]
    return max(canonical, key=lambda p: len(p.parts)) if canonical else file.parent

def columns_for(file: Path, side: str):
    names = pq.ParquetFile(file).schema.names
    low = {str(c).strip().lower(): str(c) for c in names}
    t = next((low[n] for n in TIME_NAMES if n in low), None)
    if not t:
        raise ValueError(f"{file}: no timestamp column found")
    found = {}
    for target in ("high", "low", "close"):
        aliases = [f"{side}_{target}", f"{target}_{side}", target]
        if side == "bid":
            aliases += [f"bid_{target}", f"{target}_bid"]
        aliases += [f"mid_{target}", f"{target}_mid"]
        col = next((low[a] for a in aliases if a in low), None)
        if not col:
            raise ValueError(f"{file}: missing {side} {target}")
        found[target] = col
    return t, found

def sha256(file: Path):
    h = hashlib.sha256()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="AUREON root or canonical data folder")
    ap.add_argument("--out", default="research_results/adaptive_lab")
    ap.add_argument("--side", choices=("bid", "ask", "mid"), default="bid")
    ap.add_argument("--timeframe", choices=("auto", "M1", "M5", "M15", "M30", "H1", "H4", "D1"), default="auto")
    ap.add_argument("--max-rows", type=int, default=1_200_000)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--stride", type=int, default=60)
    ap.add_argument("--lookback", type=int, default=1500)
    ap.add_argument("--min-samples", type=int, default=60)
    ap.add_argument("--cost-bps", type=float, default=8.0)
    ap.add_argument("--cost-grid-bps", default="4,8,12,20")
    args = ap.parse_args()
    root = Path(args.data)
    if not root.is_dir():
        raise FileNotFoundError(f"AUREON data root not found: {root}")
    files = sorted(root.rglob("*.parquet"))
    groups = {}
    for file in files:
        tf = timeframe(file)
        if args.timeframe != "auto" and tf != args.timeframe:
            continue
        if args.timeframe == "auto" and tf not in TF_ORDER:
            continue
        anchor = source_anchor(file, root)
        groups.setdefault((tf, anchor), []).append(file)
    if not groups:
        raise FileNotFoundError("No timeframe-labelled Parquet files found under the supplied data root.")
    ranked = sorted(groups.items(), key=lambda item: (
        TF_ORDER.index(item[0][0]), -len(item[1]),
        0 if "gold_canonical" in str(item[0][1]).lower() else 1, str(item[0][1])))
    (tf, anchor), selected = ranked[0]
    total_rows = sum(pq.ParquetFile(p).metadata.num_rows for p in selected)
    if total_rows > args.max_rows:
        raise ValueError(f"Selected {tf} partitions contain {total_rows:,} rows, above safety cap {args.max_rows:,}. Use a coarser timeframe or deliberately raise --max-rows after checking RAM.")
    print(f"[AUREON] Selected {tf}; source root={anchor}; partitions={len(selected)}; rows={total_rows:,}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    staged = out / f".staged_xauusd_{tf.lower()}.parquet"
    staged_tmp = staged.with_suffix(".parquet.tmp")
    writer = None
    try:
        for i, file in enumerate(selected, 1):
            time_col, price_cols = columns_for(file, args.side)
            frame = pd.read_parquet(file, columns=[time_col, price_cols["high"], price_cols["low"], price_cols["close"]])
            frame = frame.rename(columns={time_col: "time", price_cols["high"]: "high", price_cols["low"]: "low", price_cols["close"]: "close"})
            frame = frame[["time", "high", "low", "close"]]
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(staged_tmp, table.schema, compression="zstd")
            elif table.schema != writer.schema:
                table = table.cast(writer.schema)
            writer.write_table(table)
            if i % 100 == 0 or i == len(selected):
                print(f"[AUREON] Staged {i}/{len(selected)} partitions")
        if writer is None:
            raise RuntimeError("No usable partitions selected.")
        writer.close()
        writer = None
        pq.ParquetFile(staged_tmp)
        staged_tmp.replace(staged)
    finally:
        if writer is not None:
            writer.close()
        if staged_tmp.exists():
            staged_tmp.unlink()
    cmd = [sys.executable, "-m", "research.evolution.run_adaptive_lab",
           "--data", str(staged), "--out", str(out), "--side", args.side,
           "--max-rows", str(args.max_rows), "--horizon", str(args.horizon),
           "--stride", str(args.stride), "--lookback", str(args.lookback),
           "--min-samples", str(args.min_samples), "--cost-bps", str(args.cost_bps),
           "--cost-grid-bps", args.cost_grid_bps]
    subprocess.run(cmd, check=True)
    report_path = out / "adaptive_lab_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = []
    composite = hashlib.sha256()
    for file in selected:
        digest = sha256(file)
        rel = str(file.relative_to(root))
        manifest.append({"path": rel, "rows": pq.ParquetFile(file).metadata.num_rows, "sha256": digest})
        composite.update(rel.encode("utf-8")); composite.update(digest.encode("ascii"))
    report["source"]["source_path"] = str(root)
    report["source"]["source_root_selected"] = str(anchor)
    report["source"]["timeframe_selected"] = tf
    report["source"]["source_file_count"] = len(selected)
    report["source"]["source_sha256_composite"] = composite.hexdigest()
    report["source"]["source_files"] = manifest
    report["source"]["staged_file_sha256"] = sha256(staged)
    report["source"]["staged_file"] = str(staged)
    report["authority"]["research_only"] = True
    report["authority"]["execution_authorized"] = False
    report["authority"]["demo_orders_submitted"] = False
    report["authority"]["live_trading_allowed"] = False
    tmp = report_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(report_path)
    print(json.dumps({"report": str(report_path), "source_root": str(root), "selected_timeframe": tf,
                      "partition_count": len(selected), "rows": total_rows,
                      "first_time_utc": report["source"].get("first_time_utc"),
                      "last_time_utc": report["source"].get("last_time_utc"),
                      "coverage_years_approx": report["source"].get("coverage_years_approx"),
                      "forecast_count": report["walk_forward"].get("forecast_count"),
                      "brier_score": report["walk_forward"].get("brier_score"),
                      "prior_baseline_brier_score": report["walk_forward"].get("prior_baseline_brier_score"),
                      "proxy_net_return_sum": report["walk_forward"].get("proxy_net_return_sum"),
                      "research_only": True, "execution_authorized": False}, indent=2))

if __name__ == "__main__":
    main()
