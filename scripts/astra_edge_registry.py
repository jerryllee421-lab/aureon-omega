from __future__ import annotations

"""Create an evidence-first ASTRA edge registry.

A strategy can reach ROBUST_OOS_CANDIDATE only when it survives untouched OOS,
IID and moving-block Monte Carlo, rolling temporal validation, deterministic
spread stress, and the conservative multiple-testing diagnostic. Broker-native
confirmation remains a separate mandatory gate.
"""

import argparse
import json
from pathlib import Path


def load_rows(path: Path | None):
    if path is None or not path.exists():
        return {}
    data=json.loads(path.read_text())
    return {r.get("source_variant") or r.get("strategy_id") or r.get("name"):r for r in data}


def find_mc(root: Path, source: str):
    if not root.exists():
        return None
    for p in root.iterdir():
        q=p/"monte_carlo.json"
        if source in p.name and q.exists():
            return json.loads(q.read_text())
    return None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",type=Path,required=True)
    ap.add_argument("--monte-carlo-root",type=Path,required=True)
    ap.add_argument("--rolling",type=Path)
    ap.add_argument("--spread-stress",type=Path)
    ap.add_argument("--selection-bias",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    rows=json.loads(args.selection.read_text())
    rolling=load_rows(args.rolling)
    spreads=load_rows(args.spread_stress)
    bias=load_rows(args.selection_bias)

    registry=[]
    for row in rows:
        source=row["source_variant"]
        reasons=list(row.get("reasons",[]))
        mc=find_mc(args.monte_carlo_root,source)
        roll=rolling.get(source)
        spread=spreads.get(source)
        bias_row=bias.get(source)
        oos=row.get("oos",{})

        base_ok=(
            row.get("status")=="CANDIDATE"
            and int(oos.get("trades",0))>=20
            and float(oos.get("profit_factor",0))>=1.10
            and float(oos.get("expected_payoff",0))>0
            and float(oos.get("net_profit",0))>0
            and float(oos.get("dd_percent",999))<=8.0
        )

        mc_ok=False
        if mc:
            block=mc.get("block_bootstrap",{})
            mc_ok=(
                int(mc.get("pl_days",0))>=15
                and float(mc.get("prob_end_below_start",1))<=0.30
                and float(mc.get("prob_dd_gt_10pct",1))<=0.10
                and float(mc.get("max_dd_percentiles",{}).get("p95",999))<=12.0
                and float(block.get("prob_end_below_start",1))<=0.35
                and float(block.get("prob_dd_gt_10pct",1))<=0.15
                and float(block.get("max_dd_percentiles",{}).get("p95",999))<=15.0
            )
        rolling_ok=bool(roll and roll.get("pass"))
        spread_ok=bool(spread and spread.get("pass"))
        bias_ok=bool(bias_row and bias_row.get("status")=="SUPPORT")

        if not base_ok:
            status="REJECT"
        elif not mc:
            status="RESEARCH"; reasons.append("Monte Carlo evidence missing")
        elif not mc_ok:
            status="RESEARCH"; reasons.append("IID/block Monte Carlo stress gate failed")
        elif not rolling_ok:
            status="RESEARCH"; reasons.append("Rolling temporal robustness gate failed or missing")
        elif not spread_ok:
            status="RESEARCH"; reasons.append("Spread-stress gate failed or missing")
        elif not bias_ok:
            status="RESEARCH"; reasons.append("Multiple-testing diagnostic did not provide support")
        else:
            status="ROBUST_OOS_CANDIDATE"

        registry.append({
            "strategy_id":source,
            "status":status,
            "is":row.get("is",{}),
            "oos":oos,
            "monte_carlo":mc,
            "rolling_validation":roll,
            "spread_stress":spread,
            "selection_bias":bias_row,
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
        "# ASTRA Quantum Edge Registry V7.1","",
        "ROBUST_OOS_CANDIDATE means the research evidence survived every V7.1 gate and may proceed to broker-native confirmation. It is not a live-trading certification.","",
        "| Strategy | Status | OOS trades | OOS PF | OOS expectancy | OOS DD% | Rolling | Spread | Bias | Next gate |",
        "|---|---|---:|---:|---:|---:|---|---|---|---|"
    ]
    for r in registry:
        o=r["oos"]
        rr=r.get("rolling_validation") or {}
        ss=r.get("spread_stress") or {}
        bb=r.get("selection_bias") or {}
        lines.append(
            f"| {r['strategy_id']} | {r['status']} | {int(o.get('trades',0))} | "
            f"{float(o.get('profit_factor',0)):.2f} | {float(o.get('expected_payoff',0)):.2f} | "
            f"{float(o.get('dd_percent',0)):.2f} | {'PASS' if rr.get('pass') else 'FAIL'} | "
            f"{'PASS' if ss.get('pass') else 'FAIL'} | {bb.get('status','NO_DATA')} | {r['next_gate']} |"
        )
    (args.out/"edge_registry.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
