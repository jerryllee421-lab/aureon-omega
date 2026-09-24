from __future__ import annotations

"""Create an evidence-first ASTRA edge registry from OOS + Monte Carlo evidence."""

import argparse
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",type=Path,required=True)
    ap.add_argument("--monte-carlo-root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    rows=json.loads(args.selection.read_text())
    registry=[]
    for row in rows:
        source=row["source_variant"]
        status="REJECT"
        reasons=list(row.get("reasons",[]))
        mc_path=args.monte_carlo_root / next(
            (p.name for p in args.monte_carlo_root.iterdir() if source in p.name),
            "__missing__"
        ) / "monte_carlo.json" if args.monte_carlo_root.exists() else Path("__missing__")
        mc=None
        if mc_path.exists():
            mc=json.loads(mc_path.read_text())

        oos=row.get("oos",{})
        base_ok=(
            row.get("status")=="CANDIDATE"
            and int(oos.get("trades",0))>=20
            and float(oos.get("profit_factor",0))>=1.10
            and float(oos.get("expected_payoff",0))>0
            and float(oos.get("net_profit",0))>0
            and float(oos.get("dd_percent",999))<=8.0
        )

        if base_ok and mc:
            mc_ok=(
                int(mc.get("pl_days",0))>=15
                and float(mc.get("prob_end_below_start",1))<=0.30
                and float(mc.get("prob_dd_gt_10pct",1))<=0.10
                and float(mc.get("max_dd_percentiles",{}).get("p95",999))<=12.0
            )
            if mc_ok:
                status="ROBUST_OOS_CANDIDATE"
            else:
                status="RESEARCH"
                reasons.append("Monte Carlo stress gate not fully passed")
        elif base_ok:
            status="RESEARCH"
            reasons.append("Monte Carlo evidence missing")
        else:
            status="REJECT"

        registry.append({
            "strategy_id":source,
            "status":status,
            "is":row.get("is",{}),
            "oos":oos,
            "monte_carlo":mc,
            "pf_retention":row.get("pf_retention"),
            "components":row.get("components",{}),
            "changes":row.get("changes",{}),
            "reasons":reasons,
            "next_gate":"BROKER_NATIVE_REAL_TICK" if status=="ROBUST_OOS_CANDIDATE" else "RESEARCH",
        })

    order={"ROBUST_OOS_CANDIDATE":0,"RESEARCH":1,"REJECT":2}
    registry.sort(key=lambda r:(order[r["status"]],-float(r["oos"].get("expected_payoff",0)),-float(r["oos"].get("profit_factor",0))))

    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"edge_registry.json").write_text(json.dumps(registry,indent=2))
    lines=[
        "# ASTRA Quantum Edge Registry","",
        "No strategy is certified for live trading here. ROBUST_OOS_CANDIDATE means it may proceed to broker-native real-tick confirmation.","",
        "| Strategy | Status | OOS trades | OOS PF | OOS expectancy | OOS DD% | Next gate |",
        "|---|---|---:|---:|---:|---:|---|"
    ]
    for r in registry:
        o=r["oos"]
        lines.append(f"| {r['strategy_id']} | {r['status']} | {int(o.get('trades',0))} | {float(o.get('profit_factor',0)):.2f} | {float(o.get('expected_payoff',0)):.2f} | {float(o.get('dd_percent',0)):.2f} | {r['next_gate']} |")
    (args.out/"edge_registry.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
