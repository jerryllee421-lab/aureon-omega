from __future__ import annotations

"""Parameter-stability diagnostics for ASTRA DOE rankings.

The tool does not select a winner. It identifies broad neighborhoods where
nearby parameter configurations remain directionally consistent, which is more
robust than relying on a single peak backtest.
"""

import argparse
import json
import re
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ranking",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    rows=json.loads(args.ranking.read_text())

    ema=[]
    for r in rows:
        m=re.fullmatch(r"EMA_(\d+)_(\d+)",r.get("name",""))
        if not m:
            continue
        ema.append({
            "fast":int(m.group(1)),"slow":int(m.group(2)),
            "trades":int(r.get("trades",0)),"pf":float(r.get("pf",0)),
            "expectancy":float(r.get("expected_payoff",0)),
            "dd":float(r.get("dd_percent",0)),"score":float(r.get("score",-1e9)),
        })

    plateaus=[]
    for a in ema:
        neigh=[b for b in ema if abs(b["fast"]-a["fast"])<=5 and abs(b["slow"]-a["slow"])<=21]
        if len(neigh)<3:
            continue
        pos=[b for b in neigh if b["trades"]>=10 and b["pf"]>1 and b["expectancy"]>0]
        plateaus.append({
            "center":f"EMA_{a['fast']}_{a['slow']}",
            "neighbors":len(neigh),
            "positive_neighbors":len(pos),
            "positive_fraction":len(pos)/len(neigh),
            "median_pf":sorted([b["pf"] for b in neigh])[len(neigh)//2],
            "median_expectancy":sorted([b["expectancy"] for b in neigh])[len(neigh)//2],
        })
    plateaus.sort(key=lambda x:(x["positive_fraction"],x["median_expectancy"],x["median_pf"]),reverse=True)

    generic=[{
        "name":r.get("name"),"trades":int(r.get("trades",0)),"pf":float(r.get("pf",0)),
        "expectancy":float(r.get("expected_payoff",0)),"dd":float(r.get("dd_percent",0)),
        "score":float(r.get("score",-1e9))
    } for r in rows]

    args.out.mkdir(parents=True,exist_ok=True)
    payload={"ema_plateaus":plateaus,"ranking":generic}
    (args.out/"stability.json").write_text(json.dumps(payload,indent=2))
    lines=["# ASTRA Parameter Stability","",
           "A plateau is preferred to a single isolated optimum. This report is diagnostic; OOS remains authoritative.","",
           "| EMA center | Neighbors | Positive | Fraction | Median PF | Median expectancy |",
           "|---|---:|---:|---:|---:|---:|"]
    for p in plateaus[:20]:
        lines.append(f"| {p['center']} | {p['neighbors']} | {p['positive_neighbors']} | {p['positive_fraction']:.0%} | {p['median_pf']:.2f} | {p['median_expectancy']:.2f} |")
    (args.out/"stability.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
