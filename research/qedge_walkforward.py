from __future__ import annotations

"""Rolling walk-forward selection for ASTRA QEDGE portfolio research.

Consumes the all-variant independent-campaign ledger emitted by
research/qedge_portfolio.py. Each window selects a cascade using *only* its
training interval, freezes that choice, and evaluates the following interval.
No test-window metric participates in selection.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def max_dd_r(values: np.ndarray) -> float:
    if len(values) == 0:
        return 0.0
    eq=np.r_[0.0,np.cumsum(values)]
    peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))


def metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"campaigns":0,"expectancy_r":0.0,"pf_r":0.0,"net_r":0.0,"max_dd_r":0.0,"win_rate":0.0}
    rs=df["r"].astype(float).to_numpy()
    pos=rs[rs>0].sum()
    neg=-rs[rs<0].sum()
    return {
        "campaigns":int(len(rs)),
        "expectancy_r":float(rs.mean()),
        "pf_r":float(pos/neg) if neg>0 else (999.0 if pos>0 else 0.0),
        "net_r":float(rs.sum()),
        "max_dd_r":max_dd_r(rs),
        "win_rate":float((rs>0).mean()),
    }


def score(m: dict) -> float:
    n=int(m["campaigns"])
    if n<=0:
        return -1e9
    reliability=n/(n+40.0)
    pf=min(max(float(m["pf_r"]),0.0),4.0)
    shrunk_pf=1.0+(pf-1.0)*reliability
    shrunk_exp=float(m["expectancy_r"])*reliability
    sample=min(1.0,n/60.0)
    value=2.0*sample+2.0*(shrunk_pf-1.0)+math.tanh(shrunk_exp*3.0)-float(m["max_dd_r"])/20.0
    if n<30:
        value-=2.0*(30-n)/30.0
    return float(value)


def add_months(ts: pd.Timestamp, months: int) -> pd.Timestamp:
    return ts + pd.DateOffset(months=months)


def daily_r(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    idx=pd.DatetimeIndex(df["exit_time"]).floor("D")
    s=pd.Series(df["r"].astype(float).to_numpy(),index=idx)
    return s.groupby(level=0).sum().sort_index()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trades",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("qedge_walkforward_results"))
    ap.add_argument("--train-months",type=int,default=18)
    ap.add_argument("--test-months",type=int,default=6)
    ap.add_argument("--step-months",type=int,default=6)
    ap.add_argument("--min-train-campaigns",type=int,default=30)
    args=ap.parse_args()

    x=pd.read_parquet(args.trades)
    if x.empty:
        raise SystemExit("No QEDGE campaigns found")
    for col in ("entry_time","exit_time","signal_time"):
        x[col]=pd.to_datetime(x[col],utc=True)
    required={"strategy","cascade","entry_time","exit_time","r"}
    missing=required-set(x.columns)
    if missing:
        raise SystemExit(f"Missing campaign columns: {sorted(missing)}")

    first=x["entry_time"].min().floor("D")
    last=x["entry_time"].max().ceil("D")
    test_start=add_months(first,args.train_months)
    windows=[]
    all_test_rows=[]
    portfolio_parts=[]

    while test_start<last:
        train_start=test_start-pd.DateOffset(months=args.train_months)
        test_end=min(add_months(test_start,args.test_months),last+pd.Timedelta(days=1))
        if test_end<=test_start:
            break

        selections=[]
        selected_test=[]
        for strategy in sorted(x["strategy"].dropna().unique()):
            sx=x[x["strategy"]==strategy]
            candidates=[]
            for cascade in sorted(sx["cascade"].dropna().unique()):
                train=sx[(sx["cascade"]==cascade)&(sx["entry_time"]>=train_start)&(sx["entry_time"]<test_start)]
                m=metrics(train)
                candidates.append({"cascade":cascade,"train":m,"score":score(m)})
            eligible=[
                c for c in candidates
                if c["train"]["campaigns"]>=args.min_train_campaigns
                and c["train"]["expectancy_r"]>0
                and c["train"]["pf_r"]>1.0
            ]
            ranked=sorted(eligible if eligible else candidates,key=lambda c:c["score"],reverse=True)
            best=ranked[0]
            test=sx[(sx["cascade"]==best["cascade"])&(sx["entry_time"]>=test_start)&(sx["entry_time"]<test_end)]
            tm=metrics(test)
            selection={
                "strategy":strategy,
                "cascade":best["cascade"],
                "eligible_selection":bool(eligible),
                "train":best["train"],
                "train_score":best["score"],
                "test":tm,
            }
            selections.append(selection)
            if not test.empty:
                tt=test.copy()
                tt["wf_strategy"]=strategy
                tt["wf_cascade"]=best["cascade"]
                tt["wf_test_start"]=test_start
                selected_test.append(tt)
                s=daily_r(test).rename(strategy)
                portfolio_parts.append(pd.DataFrame({
                    "date":s.index,
                    "strategy":strategy,
                    "r":s.values,
                    "window":str(test_start.date()),
                }))

        if selected_test:
            joined=pd.concat(selected_test,ignore_index=True)
            all_test_rows.append(joined)
            daily=joined.assign(day=joined["exit_time"].dt.floor("D")).groupby(["day","strategy"])["r"].sum().unstack(fill_value=0.0)
            port=daily.mean(axis=1)
            port_metrics={
                "days":int(len(port)),
                "net_r":float(port.sum()),
                "mean_daily_r":float(port.mean()) if len(port) else 0.0,
                "positive_day_fraction":float((port>0).mean()) if len(port) else 0.0,
                "max_dd_r":max_dd_r(port.to_numpy(dtype=float)),
            }
        else:
            port_metrics={"days":0,"net_r":0.0,"mean_daily_r":0.0,"positive_day_fraction":0.0,"max_dd_r":0.0}

        windows.append({
            "train_start":str(train_start),
            "train_end_exclusive":str(test_start),
            "test_start":str(test_start),
            "test_end_exclusive":str(test_end),
            "selections":selections,
            "equal_risk_portfolio":port_metrics,
        })
        test_start=add_months(test_start,args.step_months)

    stitched=pd.concat(all_test_rows,ignore_index=True) if all_test_rows else pd.DataFrame()
    aggregate=[]
    if not stitched.empty:
        for strategy in sorted(stitched["strategy"].unique()):
            aggregate.append({"strategy":strategy,**metrics(stitched[stitched["strategy"]==strategy])})
        stitched.to_parquet(args.out/"walkforward_campaigns.parquet",index=False) if args.out.exists() else None

    # Overall equal-risk portfolio across stitched, non-overlapping test windows.
    if portfolio_parts:
        p=pd.concat(portfolio_parts,ignore_index=True)
        day_strategy=p.groupby(["date","strategy"])["r"].sum().unstack(fill_value=0.0)
        port=day_strategy.mean(axis=1)
        overall_port={
            "days":int(len(port)),
            "net_r":float(port.sum()),
            "mean_daily_r":float(port.mean()) if len(port) else 0.0,
            "positive_day_fraction":float((port>0).mean()) if len(port) else 0.0,
            "max_dd_r":max_dd_r(port.to_numpy(dtype=float)),
            "correlation":day_strategy.corr().round(4).fillna(0.0).to_dict(),
        }
    else:
        overall_port={"days":0,"net_r":0.0,"mean_daily_r":0.0,"positive_day_fraction":0.0,"max_dd_r":0.0,"correlation":{}}

    args.out.mkdir(parents=True,exist_ok=True)
    if not stitched.empty:
        stitched.to_parquet(args.out/"walkforward_campaigns.parquet",index=False)
        stitched.to_csv(args.out/"walkforward_campaigns.csv",index=False)

    payload={
        "methodology":{
            "train_months":args.train_months,
            "test_months":args.test_months,
            "step_months":args.step_months,
            "min_train_campaigns":args.min_train_campaigns,
            "selection":"development-window only; test interval never used for cascade selection",
            "unit":"independent campaign R",
            "note":"Historical walk-forward robustness, not future-unseen forward evidence.",
        },
        "windows":windows,
        "strategy_aggregate":aggregate,
        "equal_risk_portfolio":overall_port,
    }
    (args.out/"walkforward.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")

    lines=[
        "# ASTRA QEDGE Rolling Walk-Forward","",
        f"Training: {args.train_months} months · Test: {args.test_months} months · Step: {args.step_months} months","",
        "| Strategy | Test campaigns | PF(R) | Expectancy(R) | Net R | Max DD R |",
        "|---|---:|---:|---:|---:|---:|"
    ]
    for r in aggregate:
        lines.append(f"| {r['strategy']} | {r['campaigns']} | {r['pf_r']:.2f} | {r['expectancy_r']:.3f} | {r['net_r']:.2f} | {r['max_dd_r']:.2f} |")
    lines += [
        "",
        "## Equal-risk stitched test portfolio","",
        f"- Test days: {overall_port['days']}",
        f"- Net R: {overall_port['net_r']:.3f}",
        f"- Mean daily R: {overall_port['mean_daily_r']:.4f}",
        f"- Max DD R: {overall_port['max_dd_r']:.3f}",
        "",
        "Native MT5/broker confirmation and forward demo evidence remain mandatory."
    ]
    (args.out/"walkforward.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))


if __name__=="__main__":
    main()
