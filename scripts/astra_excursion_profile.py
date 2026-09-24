from __future__ import annotations

"""Summarize campaign MAE/MFE and holding-time telemetry from ASTRA event ledgers."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def fnum(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def percentile(xs, p):
    xs=sorted(x for x in xs if math.isfinite(x))
    if not xs:
        return 0.0
    k=(len(xs)-1)*p
    lo=int(math.floor(k)); hi=int(math.ceil(k))
    if lo==hi:
        return xs[lo]
    return xs[lo]*(hi-k)+xs[hi]*(k-lo)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    finals={}
    exits=defaultdict(list)
    files=0
    for p in sorted(args.root.rglob("*.csv")):
        try:
            with p.open(newline="",encoding="utf-8",errors="ignore") as fh:
                reader=csv.DictReader(fh)
                fields=set(reader.fieldnames or [])
                if not {"campaign_id","event"}.issubset(fields):
                    continue
                files+=1
                for r in reader:
                    cid=(r.get("campaign_id") or "").strip()
                    if not cid:
                        continue
                    ev=(r.get("event") or "").strip()
                    if ev=="DEAL_EXIT":
                        exits[cid].append({
                            "time":r.get("time"),
                            "price":fnum(r.get("price")),
                            "note":r.get("note",""),
                        })
                    if ev=="CAMPAIGN_FINAL":
                        finals[cid]={
                            "campaign_id":cid,
                            "direction":r.get("direction"),
                            "max_mfe_r":fnum(r.get("max_mfe_r")),
                            "max_mae_r":fnum(r.get("max_mae_r")),
                            "hold_seconds":int(fnum(r.get("hold_seconds"))),
                            "first_entry":fnum(r.get("first_entry")),
                            "initial_stop":fnum(r.get("initial_stop")),
                            "initial_risk_price":fnum(r.get("initial_risk_price")),
                            "exit_price":fnum(r.get("price")),
                            "exit_events":exits.get(cid,[]),
                        }
        except Exception:
            continue

    rows=list(finals.values())
    mfe=[r["max_mfe_r"] for r in rows]
    mae=[r["max_mae_r"] for r in rows]
    holds=[r["hold_seconds"]/60.0 for r in rows]

    summary={
        "files":files,
        "campaigns_with_final_excursion":len(rows),
        "mfe_r":{
            "p25":percentile(mfe,.25),"p50":percentile(mfe,.50),
            "p75":percentile(mfe,.75),"p90":percentile(mfe,.90),
            "mean":sum(mfe)/len(mfe) if mfe else 0.0,
        },
        "mae_r":{
            "p25":percentile(mae,.25),"p50":percentile(mae,.50),
            "p75":percentile(mae,.75),"p90":percentile(mae,.90),
            "mean":sum(mae)/len(mae) if mae else 0.0,
        },
        "hold_minutes":{
            "p25":percentile(holds,.25),"p50":percentile(holds,.50),
            "p75":percentile(holds,.75),"p90":percentile(holds,.90),
            "mean":sum(holds)/len(holds) if holds else 0.0,
        },
        "campaigns":rows,
    }

    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"excursions.json").write_text(json.dumps(summary,indent=2))
    lines=[
        "# ASTRA MAE/MFE Excursion Profile","",
        f"Files scanned: {files} · Final campaigns: {len(rows)}","",
        "| Metric | P25 | P50 | P75 | P90 | Mean |",
        "|---|---:|---:|---:|---:|---:|",
        f"| MFE (R) | {summary['mfe_r']['p25']:.2f} | {summary['mfe_r']['p50']:.2f} | {summary['mfe_r']['p75']:.2f} | {summary['mfe_r']['p90']:.2f} | {summary['mfe_r']['mean']:.2f} |",
        f"| MAE (R) | {summary['mae_r']['p25']:.2f} | {summary['mae_r']['p50']:.2f} | {summary['mae_r']['p75']:.2f} | {summary['mae_r']['p90']:.2f} | {summary['mae_r']['mean']:.2f} |",
        f"| Hold (min) | {summary['hold_minutes']['p25']:.1f} | {summary['hold_minutes']['p50']:.1f} | {summary['hold_minutes']['p75']:.1f} | {summary['hold_minutes']['p90']:.1f} | {summary['hold_minutes']['mean']:.1f} |",
        "",
        "Excursion statistics are diagnostics, not standalone promotion criteria.",
    ]
    (args.out/"excursions.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
