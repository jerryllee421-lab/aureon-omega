from __future__ import annotations

"""One-command AUREON QEDGE research pipeline.

Runs on ordinary Python/Linux/Windows compute and does not require MetaTrader.
Native MT5 is intentionally deferred until historical candidates survive.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MIRROR_COMMIT="922f83a60cc574e7395fb27397077288055a1ef6"


def run(cmd, timeout=None):
    printable=" ".join(str(x) for x in cmd)
    print(f"$ {printable}", flush=True)
    subprocess.run([str(x) for x in cmd], check=True, timeout=timeout)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",default="research_data")
    ap.add_argument("--out",default="qedge_run")
    ap.add_argument("--skip-download",action="store_true")
    ap.add_argument("--start",default="2021-08-20")
    ap.add_argument("--end",default="2026-08-20")
    ap.add_argument("--holdout-start",default="2026-04-20")
    args=ap.parse_args()

    root=Path(args.data_root)
    out=Path(args.out)
    portfolio=out/"portfolio"
    wf=out/"walkforward"
    out.mkdir(parents=True,exist_ok=True)

    manifest=root/"XAUUSD"/"download_manifest.json"
    if not args.skip_download:
        run([
            sys.executable,"research/mirror_m1.py",
            "--start",args.start,
            "--end",args.end,
            "--commit",MIRROR_COMMIT,
            "--output",root,
        ],timeout=3600)
    elif not manifest.exists():
        raise SystemExit("--skip-download requested but dataset manifest is missing")

    run([
        sys.executable,"research/qedge_portfolio.py",
        "--root",root,
        "--out",portfolio,
        "--start",args.start,
        "--end",args.end,
        "--holdout-start",args.holdout_start,
        "--reward-risk","2.0",
        "--max-hold-hours","8",
    ],timeout=7200)

    trades=portfolio/"trades.parquet"
    if not trades.exists():
        raise SystemExit("Portfolio engine produced no trade ledger")

    run([
        sys.executable,"research/qedge_walkforward.py",
        "--trades",trades,
        "--out",wf,
        "--train-months","18",
        "--test-months","6",
        "--step-months","6",
        "--min-train-campaigns","30",
    ],timeout=1800)

    data_meta=json.loads(manifest.read_text()) if manifest.exists() else {}
    payload={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "pipeline":"AUREON_QEDGE_5Y_V1",
        "data":{
            "mirror_commit":data_meta.get("mirror_commit",MIRROR_COMMIT),
            "dataset_sha256":data_meta.get("dataset_sha256"),
            "actual_first":data_meta.get("actual_first"),
            "actual_last":data_meta.get("actual_last"),
            "m1_rows":data_meta.get("m1_rows"),
        },
        "research":{
            "portfolio_report":str(portfolio/"report.json"),
            "walkforward_report":str(wf/"walkforward.json"),
            "performance_unit":"R",
            "campaign_unit":"independent campaign",
            "broker_native_required":True,
            "forward_demo_required":True,
            "live_trading":False,
        },
    }
    (out/"run_manifest.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2))


if __name__=="__main__":
    main()
