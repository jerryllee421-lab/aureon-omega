from __future__ import annotations

"""Matched-signal execution A/B analysis for ASTRA tester ledgers.

Campaign IDs are derived from direction + sweep time, so variants that preserve
the signal-generation rules can be compared on the same qualified setups. This
tool is diagnostic only: it compares execution/fill behavior and realized
campaign P/L for common signals; it does not promote a strategy.
"""

import argparse
import csv
import json
import math
import re
from pathlib import Path

PNL_RE=re.compile(r"(?:^|\s)pnl=(-?\d+(?:\.\d+)?)",re.I)


def fnum(x,default=0.0):
    try: return float(x)
    except Exception: return default


def read_case(path: Path):
    campaigns={}
    with path.open(newline="",encoding="utf-8",errors="ignore") as fh:
        rd=csv.DictReader(fh)
        for r in rd:
            cid=(r.get("campaign_id") or "").strip()
            if not cid:
                continue
            x=campaigns.setdefault(cid,{
                "signal":False,"filled":False,"completed":False,"pnl":0.0,
                "max_mfe_r":0.0,"max_mae_r":0.0,"hold_seconds":0,
                "direction":(r.get("direction") or "").strip(),
            })
            ev=(r.get("event") or "").strip()
            state=(r.get("state") or "").strip()
            note=(r.get("note") or "").strip()
            if ev=="SIGNAL_QUALIFIED" or state=="ASTRA_ENTRY_ZONE_ACTIVE":
                x["signal"]=True
            if ev=="E1_OPEN" or ev.endswith("_PENDING_FILLED"):
                x["filled"]=True
            if ev=="CAMPAIGN_FINAL":
                x["completed"]=True
                x["max_mfe_r"]=max(x["max_mfe_r"],fnum(r.get("max_mfe_r")))
                x["max_mae_r"]=max(x["max_mae_r"],fnum(r.get("max_mae_r")))
                x["hold_seconds"]=max(x["hold_seconds"],int(fnum(r.get("hold_seconds"))))
            if ev=="DEAL_EXIT":
                m=PNL_RE.search(note)
                if m:
                    x["pnl"]+=float(m.group(1))
    return campaigns


def mean(xs):
    return sum(xs)/len(xs) if xs else 0.0


def summary(campaigns):
    sig={k:v for k,v in campaigns.items() if v["signal"]}
    fills={k:v for k,v in sig.items() if v["filled"]}
    completed={k:v for k,v in fills.items() if v["completed"]}
    pnls=[v["pnl"] for v in fills.values()]
    return {
        "qualified_signals":len(sig),
        "filled_campaigns":len(fills),
        "fill_rate":len(fills)/len(sig) if sig else 0.0,
        "completed_campaigns":len(completed),
        "total_pnl":sum(pnls),
        "mean_pnl_per_qualified_signal":sum(pnls)/len(sig) if sig else 0.0,
        "mean_pnl_per_fill":mean(pnls),
        "positive_fill_fraction":sum(v>0 for v in pnls)/len(pnls) if pnls else 0.0,
        "mean_mfe_r":mean([v["max_mfe_r"] for v in completed.values()]),
        "mean_mae_r":mean([v["max_mae_r"] for v in completed.values()]),
        "mean_hold_minutes":mean([v["hold_seconds"]/60 for v in completed.values()]),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--ledgers",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--baseline",default="BASE_DISCOVERY")
    args=ap.parse_args()

    manifest=json.loads(args.manifest.read_text())
    execution_cases=[]
    for c in manifest:
        ch=c.get("changes",{})
        if c["name"]==args.baseline or any(k in ch for k in (
            "InpExecutionMode","InpEntryStyle","InpPendingPriceOffsetATR",
            "InpPendingExpiryBars","InpMaxEntryExtensionATR","InpHardRejectExtensionATR"
        )):
            execution_cases.append(c)

    data={}
    missing=[]
    for c in execution_cases:
        p=args.ledgers/f"{c['name']}.csv"
        if not p.exists():
            missing.append(c["name"])
            continue
        data[c["name"]]=read_case(p)

    rows=[]
    for c in execution_cases:
        if c["name"] not in data:
            continue
        rows.append({
            "name":c["name"],
            "changes":c.get("changes",{}),
            **summary(data[c["name"]]),
        })

    paired=[]
    base=data.get(args.baseline)
    if base:
        base_sig={k:v for k,v in base.items() if v["signal"]}
        for c in execution_cases:
            name=c["name"]
            if name==args.baseline or name not in data:
                continue
            var_sig={k:v for k,v in data[name].items() if v["signal"]}
            common=sorted(set(base_sig)&set(var_sig))
            if not common:
                continue
            bp=[]; vp=[]
            bfill=vfill=0
            for cid in common:
                b=base_sig[cid]; v=var_sig[cid]
                if b["filled"]: bfill+=1
                if v["filled"]: vfill+=1
                bp.append(b["pnl"] if b["filled"] else 0.0)
                vp.append(v["pnl"] if v["filled"] else 0.0)
            deltas=[v-b for b,v in zip(bp,vp)]
            paired.append({
                "variant":name,
                "common_signals":len(common),
                "baseline_fills":bfill,
                "variant_fills":vfill,
                "baseline_mean_pnl_per_common_signal":mean(bp),
                "variant_mean_pnl_per_common_signal":mean(vp),
                "mean_paired_pnl_delta":mean(deltas),
                "positive_delta_fraction":sum(d>0 for d in deltas)/len(deltas),
            })

    args.out.mkdir(parents=True,exist_ok=True)
    payload={
        "baseline":args.baseline,
        "variants":rows,
        "paired_vs_baseline":paired,
        "missing_ledgers":missing,
        "method":"matched campaign_id (direction+sweep time); unfilled common signals count as zero P/L",
        "promotion_authority":False,
    }
    (args.out/"execution_ab.json").write_text(json.dumps(payload,indent=2))
    lines=[
        "# ASTRA Matched-Signal Execution A/B","",
        "Same-signal comparison only. This report is diagnostic and cannot promote a strategy.","",
        "| Variant | Signals | Fills | Fill rate | Total P/L | Mean P/L/signal | Mean MFE R | Mean MAE R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['qualified_signals']} | {r['filled_campaigns']} | "
            f"{r['fill_rate']:.1%} | {r['total_pnl']:.2f} | "
            f"{r['mean_pnl_per_qualified_signal']:.2f} | {r['mean_mfe_r']:.2f} | {r['mean_mae_r']:.2f} |"
        )
    lines += ["","## Paired vs baseline","",
              "| Variant | Common signals | Base fills | Variant fills | Base mean P/L | Variant mean P/L | Paired delta |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for r in paired:
        lines.append(
            f"| {r['variant']} | {r['common_signals']} | {r['baseline_fills']} | {r['variant_fills']} | "
            f"{r['baseline_mean_pnl_per_common_signal']:.2f} | {r['variant_mean_pnl_per_common_signal']:.2f} | "
            f"{r['mean_paired_pnl_delta']:.2f} |"
        )
    if missing:
        lines += ["",f"Missing per-case ledgers: {', '.join(missing)}"]
    (args.out/"execution_ab.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
