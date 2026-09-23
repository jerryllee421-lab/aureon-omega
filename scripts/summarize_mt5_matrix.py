#!/usr/bin/env python3
"""Summarize ASTRA MT5 experiment reports without hiding failed candidates."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def val(m,key,default=0.0):
    x=m.get(key,default)
    if isinstance(x,dict):
        try:return float(x.get("value",default))
        except:return default
    try:return float(x)
    except:return default

def pct(m,key,default=0.0):
    x=m.get(key,{})
    if isinstance(x,dict) and x.get("percent") is not None:
        try:return float(x["percent"])
        except:return default
    return default

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--out",type=Path,default=None)
    args=ap.parse_args()
    rows=[]
    for p in sorted(args.root.glob("*/mt5_metrics.json")):
        d=json.loads(p.read_text())
        m=d.get("metrics",{})
        dd=max(pct(m,"max_equity_dd_relative"),pct(m,"max_balance_dd_relative"))
        rows.append({
            "variant":p.parent.name,
            "trades":int(val(m,"total_trades")),
            "net_profit":val(m,"net_profit"),
            "profit_factor":val(m,"profit_factor"),
            "expected_payoff":val(m,"expected_payoff"),
            "drawdown_percent":dd,
            "sharpe":val(m,"sharpe_ratio"),
            "recovery_factor":val(m,"recovery_factor"),
            "gate_pass":bool(d.get("gate_pass",False)),
        })
    if not rows:
        raise SystemExit("No mt5_metrics.json files found")

    # Descriptive ordering only. Promotion remains gated and must not depend on
    # a single composite score.
    rows_sorted=sorted(rows,key=lambda r:(r["gate_pass"],r["expected_payoff"],r["profit_factor"],-r["drawdown_percent"]),reverse=True)
    payload={"variants":rows_sorted}
    out=args.out or args.root
    out.mkdir(parents=True,exist_ok=True)
    (out/"matrix_summary.json").write_text(json.dumps(payload,indent=2))

    lines=["# ASTRA MT5 Experiment Summary","",
           "This table is descriptive. A configuration is not promoted from one metric or one sample window.","",
           "| Variant | Trades | Net P/L | PF | Expected payoff | DD % | Sharpe | Recovery | Gate |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows_sorted:
        lines.append(f"| {r['variant']} | {r['trades']} | {r['net_profit']:.2f} | {r['profit_factor']:.3f} | {r['expected_payoff']:.3f} | {r['drawdown_percent']:.2f} | {r['sharpe']:.3f} | {r['recovery_factor']:.3f} | {'PASS' if r['gate_pass'] else 'FAIL'} |")
    lines += ["",
      "## Interpretation gates","",
      "- Treat zero-trade variants as diagnostic failures, not neutral results.",
      "- The DISCOVERY variant is diagnostic only and cannot be promoted to forward testing.",
      "- Pending Precision must improve execution quality or risk-adjusted expectancy without unacceptable fill-rate loss.",
      "- Promotion requires subsequent out-of-sample and walk-forward evidence."
    ]
    (out/"matrix_summary.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))

if __name__=="__main__":
    main()
