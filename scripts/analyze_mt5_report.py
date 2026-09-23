#!/usr/bin/env python3
"""ASTRA MT5 Strategy Tester report analyzer.

Reads an MT5 Strategy Tester XML/HTML report and writes normalized JSON + Markdown.
Fails the CI gate when hard robustness thresholds are violated.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import xml.etree.ElementTree as ET

LABELS = {
    "Total Net Profit": "net_profit",
    "Profit Factor": "profit_factor",
    "Expected Payoff": "expected_payoff",
    "Equity Drawdown Maximal": "max_equity_dd",
    "Equity Drawdown Relative": "max_equity_dd_relative",
    "Balance Drawdown Maximal": "max_balance_dd",
    "Balance Drawdown Relative": "max_balance_dd_relative",
    "Total Trades": "total_trades",
    "Profit Trades (% of total)": "profit_trades",
    "Loss Trades (% of total)": "loss_trades",
    "Sharpe Ratio": "sharpe_ratio",
    "Recovery Factor": "recovery_factor",
}

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

def number(s: str):
    s=clean(s)
    pct=re.search(r"(-?[\d.,]+)\s*%",s)
    main=re.search(r"-?[\d][\d ,]*(?:\.\d+)?",s)
    if not main: return s
    try: value=float(main.group(0).replace(" ","").replace(",",""))
    except ValueError: return s
    return {"value":value,"percent":float(pct.group(1).replace(",","")) if pct else None,"raw":s}

def cells_from_xml(path: Path):
    root=ET.parse(path).getroot()
    return [clean(" ".join(e.itertext())) for e in root.iter() if clean(" ".join(e.itertext()))]

def cells_from_html(path: Path):
    txt=path.read_text(errors="ignore")
    txt=re.sub(r"<script.*?</script>|<style.*?</style>"," ",txt,flags=re.I|re.S)
    txt=re.sub(r"<[^>]+>","\n",txt)
    return [clean(x) for x in txt.splitlines() if clean(x)]

def extract(cells):
    metrics={}
    for i,c in enumerate(cells):
        for label,key in LABELS.items():
            if c==label or c.startswith(label+":"):
                tail=c.split(":",1)[1].strip() if ":" in c else ""
                val=tail
                if not val:
                    for j in range(i+1,min(i+5,len(cells))):
                        if cells[j] not in LABELS and cells[j] != c:
                            val=cells[j]; break
                metrics[key]=number(val)
    return metrics

def val(metrics,key,default=0.0):
    x=metrics.get(key,default)
    return float(x.get("value",default)) if isinstance(x,dict) else default

def pct(metrics,key,default=0.0):
    x=metrics.get(key,{})
    if isinstance(x,dict) and x.get("percent") is not None: return float(x["percent"])
    raw=x.get("raw","") if isinstance(x,dict) else ""
    m=re.search(r"([\d.]+)\s*%",raw)
    return float(m.group(1)) if m else default

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("report",type=Path)
    ap.add_argument("--out",type=Path,default=Path("research/results"))
    ap.add_argument("--min-trades",type=int,default=100)
    ap.add_argument("--min-pf",type=float,default=1.10)
    ap.add_argument("--max-dd",type=float,default=20.0)
    args=ap.parse_args()
    cells=cells_from_xml(args.report) if args.report.suffix.lower()==".xml" else cells_from_html(args.report)
    metrics=extract(cells)
    trades=int(val(metrics,"total_trades"))
    pf=val(metrics,"profit_factor")
    dd=max(pct(metrics,"max_equity_dd_relative"),pct(metrics,"max_balance_dd_relative"))
    gates={
        "sample_size": {"pass":trades>=args.min_trades,"actual":trades,"minimum":args.min_trades},
        "profit_factor": {"pass":pf>=args.min_pf,"actual":pf,"minimum":args.min_pf},
        "drawdown": {"pass":dd<=args.max_dd,"actual_percent":dd,"maximum_percent":args.max_dd},
    }
    passed=all(g["pass"] for g in gates.values())
    payload={"source":str(args.report),"metrics":metrics,"gates":gates,"gate_pass":passed}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"mt5_metrics.json").write_text(json.dumps(payload,indent=2))
    lines=["# ASTRA MT5 Test Report","",f"**Robustness gate:** {'PASS' if passed else 'FAIL'}","",
           "| Metric | Result |","|---|---:|"]
    for k,v in metrics.items(): lines.append(f"| {k} | {v.get('raw',v) if isinstance(v,dict) else v} |")
    lines += ["","## Gates",""]
    for k,g in gates.items(): lines.append(f"- **{k}:** {'PASS' if g['pass'] else 'FAIL'} — {g}")
    (args.out/"mt5_report.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(payload,indent=2))
    raise SystemExit(0 if passed else 2)

if __name__=="__main__": main()
