from __future__ import annotations

"""Conservative multiple-testing diagnostic for ASTRA candidates.

Uses daily closed-deal P/L from the Monte Carlo evidence. The test is a
one-sided normal approximation for mean daily P/L > 0, then applies a
Bonferroni correction using the declared number of screened hypotheses.
It is deliberately conservative and is evidence only, not a profitability
guarantee.
"""

import argparse
import json
import math
import statistics
from pathlib import Path


def normal_sf(z: float) -> float:
    return 0.5*math.erfc(z/math.sqrt(2.0))


def find_mc(root: Path, source: str):
    if not root.exists():
        return None
    for p in root.iterdir():
        q=p/"monte_carlo.json"
        if source in p.name and q.exists():
            return q
    return None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",type=Path,required=True)
    ap.add_argument("--monte-carlo-root",type=Path,required=True)
    ap.add_argument("--trials",type=int,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    rows=json.loads(args.selection.read_text())
    result=[]
    for row in rows:
        source=row["source_variant"]
        q=find_mc(args.monte_carlo_root,source)
        if not q:
            result.append({"source_variant":source,"status":"NO_DATA"})
            continue
        mc=json.loads(q.read_text())
        pls=[float(v) for _,v in sorted(mc.get("daily_pl",{}).items())]
        n=len(pls)
        mean=statistics.fmean(pls) if pls else 0.0
        sd=statistics.stdev(pls) if n>=2 else 0.0
        se=sd/math.sqrt(n) if n>=2 and sd>0 else 0.0
        z=mean/se if se>0 else 0.0
        p=normal_sf(z) if se>0 else 1.0
        p_adj=min(1.0,p*max(1,args.trials))
        status="SUPPORT" if n>=20 and mean>0 and p_adj<=0.10 else "WEAK_OR_INSUFFICIENT"
        result.append({
            "source_variant":source,
            "status":status,
            "pl_days":n,
            "daily_mean":mean,
            "daily_sd":sd,
            "z_vs_zero":z,
            "one_sided_p":p,
            "bonferroni_trials":args.trials,
            "bonferroni_p":p_adj,
        })

    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"selection_bias.json").write_text(json.dumps(result,indent=2))
    lines=[
        "# ASTRA Multiple-Testing Diagnostic","",
        f"Declared screened hypotheses: {args.trials}",
        "Bonferroni-adjusted one-sided daily-P/L test. This is deliberately conservative and diagnostic only.","",
        "| Candidate | P/L days | Mean/day | z | raw p | adjusted p | Evidence |",
        "|---|---:|---:|---:|---:|---:|---|"
    ]
    for r in result:
        if r["status"]=="NO_DATA":
            lines.append(f"| {r['source_variant']} | 0 | — | — | — | — | NO_DATA |")
        else:
            lines.append(
                f"| {r['source_variant']} | {r['pl_days']} | {r['daily_mean']:.2f} | {r['z_vs_zero']:.2f} | "
                f"{r['one_sided_p']:.4g} | {r['bonferroni_p']:.4g} | {r['status']} |"
            )
    (args.out/"selection_bias.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
