from __future__ import annotations

"""Aggregate ASTRA candidate performance under deterministic spread stress."""

import argparse
import json
from pathlib import Path


def m(path,key,default=0.0):
    try:
        d=json.loads(path.read_text())
        return float(d["metrics"][key]["value"])
    except Exception:
        return default


def dd(path):
    try:
        d=json.loads(path.read_text())
        vals=[]
        for k in ("max_equity_dd_relative","max_balance_dd_relative"):
            x=d["metrics"].get(k,{})
            if isinstance(x,dict):
                vals.append(float(x.get("percent") if x.get("percent") is not None else x.get("value",0)))
        return max(vals or [0.0])
    except Exception:
        return 0.0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    manifest=json.loads(args.manifest.read_text())

    rows=[]
    for case in manifest:
        name=case["name"]
        stresses=[]
        for sdir in sorted(args.root.iterdir()) if args.root.exists() else []:
            p=sdir/"analysis"/name/"mt5_metrics.json"
            if not p.exists():
                continue
            label=sdir.name
            try:
                mult=float(label.replace("spread_","").replace("x",""))
            except Exception:
                mult=0.0
            row={
                "label":label,"multiplier":mult,
                "trades":int(m(p,"total_trades")),
                "profit_factor":m(p,"profit_factor"),
                "expected_payoff":m(p,"expected_payoff"),
                "net_profit":m(p,"net_profit"),
                "dd_percent":dd(p),
            }
            row["positive"]=row["trades"]>=5 and row["profit_factor"]>1 and row["expected_payoff"]>0 and row["net_profit"]>0
            stresses.append(row)

        # Require survival through 1.50x spread. 2.00x is reported as a tail stress
        # but is not a mandatory promotion gate.
        required=[s for s in stresses if 1.0<=s["multiplier"]<=1.50+1e-9]
        passed=len(required)>=3 and all(s["positive"] and s["dd_percent"]<=12.0 for s in required)
        rows.append({
            "source_variant":case.get("source_variant",name),
            "name":name,
            "pass":passed,
            "stresses":stresses,
        })

    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"spread_stress.json").write_text(json.dumps(rows,indent=2))
    lines=[
        "# ASTRA Spread Stress","",
        "Promotion gate requires positive behavior through 1.50× the observed external-data spread. 2.00× is a tail diagnostic.","",
        "| Candidate | 1.00× | 1.25× | 1.50× | 2.00× | Gate |",
        "|---|---|---|---|---|---|"
    ]
    for r in rows:
        cells={}
        for s in r["stresses"]:
            cells[round(s["multiplier"],2)]=f"PF {s['profit_factor']:.2f}, exp {s['expected_payoff']:.2f}"
        lines.append(
            f"| {r['source_variant']} | {cells.get(1.0,'—')} | {cells.get(1.25,'—')} | "
            f"{cells.get(1.5,'—')} | {cells.get(2.0,'—')} | {'PASS' if r['pass'] else 'FAIL'} |"
        )
    (args.out/"spread_stress.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
