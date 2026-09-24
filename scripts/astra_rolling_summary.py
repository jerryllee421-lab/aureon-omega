from __future__ import annotations

"""Aggregate ASTRA candidate metrics across rolling temporal validation windows."""

import argparse
import json
import statistics
from pathlib import Path


def metric(path: Path, key: str, default=0.0):
    try:
        d=json.loads(path.read_text())
        return float(d["metrics"][key]["value"])
    except Exception:
        return default


def dd(path: Path):
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
    ap.add_argument("--root",type=Path,required=True,
                    help="Directory containing per-window analysis folders")
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    manifest=json.loads(args.manifest.read_text())
    rows=[]
    for case in manifest:
        name=case["name"]
        windows=[]
        for w in sorted(args.root.iterdir()) if args.root.exists() else []:
            p=w/name/"mt5_metrics.json"
            if not p.exists():
                continue
            trades=int(metric(p,"total_trades"))
            pf=metric(p,"profit_factor")
            exp=metric(p,"expected_payoff")
            net=metric(p,"net_profit")
            d=dd(p)
            windows.append({
                "window":w.name,"trades":trades,"profit_factor":pf,
                "expected_payoff":exp,"net_profit":net,"dd_percent":d,
                "positive":trades>=5 and exp>0 and net>0 and pf>1.0,
            })
        positive=sum(1 for w in windows if w["positive"])
        n=len(windows)
        pfs=[w["profit_factor"] for w in windows]
        exps=[w["expected_payoff"] for w in windows]
        trades=sum(w["trades"] for w in windows)
        row={
            "source_variant":case.get("source_variant",name),
            "name":name,
            "windows":windows,
            "window_count":n,
            "positive_windows":positive,
            "positive_fraction":positive/n if n else 0.0,
            "total_window_trades":trades,
            "median_pf":statistics.median(pfs) if pfs else 0.0,
            "median_expectancy":statistics.median(exps) if exps else 0.0,
            "worst_dd_percent":max((w["dd_percent"] for w in windows),default=0.0),
        }
        row["pass"]=(
            n>=4 and positive>=3 and trades>=20
            and row["median_pf"]>=1.0 and row["median_expectancy"]>0
            and row["worst_dd_percent"]<=12.0
        )
        rows.append(row)

    rows.sort(key=lambda r:(not r["pass"],-r["positive_fraction"],-r["median_expectancy"],-r["median_pf"]))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"rolling_validation.json").write_text(json.dumps(rows,indent=2))
    lines=[
        "# ASTRA Rolling Temporal Validation","",
        "Fixed candidates are evaluated across four sequential calendar windows. This is a temporal robustness gate, not a substitute for untouched OOS.","",
        "| Candidate | Positive windows | Total trades | Median PF | Median expectancy | Worst DD% | Gate |",
        "|---|---:|---:|---:|---:|---:|---|"
    ]
    for r in rows:
        lines.append(
            f"| {r['source_variant']} | {r['positive_windows']}/{r['window_count']} | "
            f"{r['total_window_trades']} | {r['median_pf']:.2f} | {r['median_expectancy']:.2f} | "
            f"{r['worst_dd_percent']:.2f} | {'PASS' if r['pass'] else 'FAIL'} |"
        )
    (args.out/"rolling_validation.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
