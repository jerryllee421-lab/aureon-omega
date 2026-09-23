from __future__ import annotations

"""Build a conservative promotion table from ASTRA in-sample and OOS results.

No configuration is promoted solely because it ranks first in-sample. A
candidate must keep positive expectancy and acceptable drawdown on the untouched
OOS window. Broker-native real-tick confirmation is still mandatory afterward.
"""

import argparse
import json
from pathlib import Path


def mval(d, key, default=0.0):
    try:
        return float(d["metrics"][key]["value"])
    except Exception:
        return default


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--screen-ranking", required=True)
    ap.add_argument("--oos-manifest", required=True)
    ap.add_argument("--oos-analysis", required=True)
    ap.add_argument("--out", required=True)
    args=ap.parse_args()

    screen={x["name"]:x for x in json.loads(Path(args.screen_ranking).read_text())}
    manifest=json.loads(Path(args.oos_manifest).read_text())
    rows=[]

    for item in manifest:
        source=item["source_variant"]
        p=Path(args.oos_analysis)/item["name"]/"mt5_metrics.json"
        if not p.exists():
            continue
        d=json.loads(p.read_text())
        oos={
            "trades":int(mval(d,"total_trades")),
            "net_profit":mval(d,"net_profit"),
            "profit_factor":mval(d,"profit_factor"),
            "expected_payoff":mval(d,"expected_payoff"),
            "dd_percent":max(mval(d,"max_equity_dd_relative"),mval(d,"max_balance_dd_relative")),
            "sharpe":mval(d,"sharpe_ratio"),
        }
        ins=screen.get(source,{})
        pf_is=float(ins.get("pf",0.0))
        exp_is=float(ins.get("expected_payoff",0.0))
        pf_ret=(oos["profit_factor"]/pf_is) if pf_is>0 else 0.0
        exp_same_sign=(exp_is>0 and oos["expected_payoff"]>0)

        status="REJECT"
        reasons=[]
        if int(ins.get("trades",0)) < 10:
            reasons.append("IS sample <10")
        if pf_is < 1.05 or exp_is <= 0:
            reasons.append("IS edge weak/non-positive")
        if oos["trades"] < 5:
            reasons.append("OOS sample <5")
        if oos["profit_factor"] < 1.05 or oos["expected_payoff"] <= 0 or oos["net_profit"] <= 0:
            reasons.append("OOS edge non-positive/weak")
        if oos["dd_percent"] > 10.0:
            reasons.append("OOS drawdown >10%")
        if pf_ret < 0.60:
            reasons.append("PF retention <60%")

        if not reasons:
            status="CANDIDATE"
        elif (oos["expected_payoff"]>0 and oos["net_profit"]>0 and oos["dd_percent"]<=10.0):
            status="RESEARCH"

        rows.append({
            "source_variant":source,
            "status":status,
            "is":{k:ins.get(k) for k in ("trades","pf","expected_payoff","net_profit","dd_percent","sharpe","win_rate","score")},
            "oos":oos,
            "pf_retention":pf_ret,
            "expectancy_sign_retained":exp_same_sign,
            "reasons":reasons,
            "components":item.get("components",{}),
            "changes":item.get("changes",{}),
        })

    order={"CANDIDATE":0,"RESEARCH":1,"REJECT":2}
    rows.sort(key=lambda r:(order[r["status"]],-r["oos"]["expected_payoff"],-r["oos"]["profit_factor"],r["oos"]["dd_percent"]))

    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"candidate_selection.json").write_text(json.dumps(rows,indent=2))
    lines=[
        "# ASTRA Candidate Selection",
        "",
        "Selection requires positive untouched OOS behavior. Broker-native real-tick confirmation remains mandatory.",
        "",
        "| Variant | Status | IS trades | IS PF | OOS trades | OOS PF | OOS exp | OOS net | OOS DD% | PF retention |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['source_variant']} | {r['status']} | {int(r['is'].get('trades') or 0)} | "
            f"{float(r['is'].get('pf') or 0):.2f} | {r['oos']['trades']} | {r['oos']['profit_factor']:.2f} | "
            f"{r['oos']['expected_payoff']:.2f} | {r['oos']['net_profit']:.2f} | {r['oos']['dd_percent']:.2f} | "
            f"{r['pf_retention']*100:.0f}% |"
        )
    (out/"candidate_selection.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
