"""First-pass bar-based SMC variant evaluation; diagnostics only, not tick execution.

Signals use completed bars. Entries occur at the next bar open. OHLC ambiguity
resolves stop before target. Cost assumptions are explicit and stressed by caller.
Use quote_execution.py for quote-level evaluation before drawing execution claims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from research.tools.smc_intraday_candidates import build_candidates

VARIANTS = {
    "bos_continuation": ("bos_up", "bos_down"),
    "choch_reversal": ("choch_up", "choch_down"),
    "sweep_reclaim": ("sell_side_sweep_reclaim", "buy_side_sweep_reclaim"),
    "support_resistance": ("sr_reversal_long", "sr_reversal_short"),
    "trendline_break": ("trendline_long", "trendline_short"),
    "candle_pattern": ("pattern_long", "pattern_short"),
    "smc_displacement": ("smc_long", "smc_short"),
    "combined_candidates": ("candidate_long", "candidate_short"),
}

def _simulate(x, long_col, short_col, start, end, *, stop_atr=1.5,
              target_r=2.0, max_hold=24, spread_cost=0.8, slippage=0.35):
    trades=[]
    i=max(start, 1)
    while i < min(end, len(x)-1):
        row=x.iloc[i]
        side=1 if bool(row.get(long_col, False)) else (-1 if bool(row.get(short_col, False)) else 0)
        if side == 0 or not np.isfinite(row.atr) or row.atr <= 0:
            i += 1; continue
        entry_i=i+1
        if entry_i >= end: break
        entry=float(x.open.iloc[entry_i])
        risk=float(row.atr)*stop_atr
        stop=entry-side*risk
        target=entry+side*risk*target_r
        last=min(end, entry_i+max_hold)
        exit_price=None; reason="TIME"
        exit_i=last-1
        for j in range(entry_i, last):
            hi,lo=float(x.high.iloc[j]),float(x.low.iloc[j])
            stop_hit=(lo<=stop) if side==1 else (hi>=stop)
            target_hit=(hi>=target) if side==1 else (lo<=target)
            if stop_hit:
                exit_price=stop-side*slippage
                reason="SL"; exit_i=j; break
            if target_hit:
                exit_price=target
                reason="TP"; exit_i=j; break
        if exit_price is None:
            exit_price=float(x.close.iloc[exit_i])-side*slippage
        gross=(exit_price-entry)*side
        # Spread cost is expressed as a round-trip price-unit deduction.
        net=gross-spread_cost
        trades.append({"entry_index":entry_i,"exit_index":exit_i,"side":side,
                       "gross_price_units":gross,"net_price_units":net,"reason":reason,
                       "risk_price_units":risk})
        i=exit_i+1
    return trades

def _metrics(trades):
    net=np.array([t["net_price_units"] for t in trades],dtype=float)
    wins=net[net>0]; losses=net[net<0]
    pf=float(wins.sum()/abs(losses.sum())) if len(losses) and len(wins) else (float("inf") if len(wins) else 0.0)
    equity=np.r_[0.0, np.cumsum(net)]
    dd=float(np.max(np.maximum.accumulate(equity)-equity)) if len(equity) else 0.0
    return {"trades":len(net),"net_price_units":round(float(net.sum()),4),
            "expectancy_price_units":round(float(net.mean()),4) if len(net) else None,
            "profit_factor":round(pf,4) if np.isfinite(pf) else "INF",
            "win_rate":round(float((net>0).mean()),4) if len(net) else None,
            "max_drawdown_price_units":round(dd,4)}

def evaluate(bars, *, oos_fraction=0.3, spread_cost=0.8, slippage=0.35,
             stop_atr=1.5, target_r=2.0, max_hold=24):
    if not 0.1 <= oos_fraction <= 0.5: raise ValueError("oos_fraction must be 0.1..0.5")
    x=build_candidates(bars)
    split=int(len(x)*(1-oos_fraction))
    if split < 1 or len(x)-split < 1: raise ValueError("not enough bars for chronological split")
    report={"bars":len(x),"split_index":split,"cost_model":"bar OHLC; fixed round-trip spread deduction plus stop slippage; stop-first ambiguity; not tick execution","variants":{}}
    for name,(lc,sc) in VARIANTS.items():
        all_trades=_simulate(x,lc,sc,0,len(x),stop_atr=stop_atr,target_r=target_r,max_hold=max_hold,spread_cost=spread_cost,slippage=slippage)
        oos=[t for t in all_trades if t["entry_index"]>=split]
        ins=[t for t in all_trades if t["entry_index"]<split]
        report["variants"][name]={"all":_metrics(all_trades),"in_sample":_metrics(ins),"out_of_sample":_metrics(oos)}
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",help="CSV with timestamp,open,high,low,close")
    p.add_argument("--output",default="smc_variant_report.json")
    p.add_argument("--oos-fraction",type=float,default=.3)
    p.add_argument("--spread-cost",type=float,default=.8)
    p.add_argument("--slippage",type=float,default=.35)
    a=p.parse_args()
    df=pd.read_csv(a.input)
    if "timestamp" not in df: raise ValueError("CSV must include timestamp")
    df["timestamp"]=pd.to_datetime(df.timestamp,utc=True,errors="raise")
    df=df.set_index("timestamp").sort_index()
    result=evaluate(df,oos_fraction=a.oos_fraction,spread_cost=a.spread_cost,slippage=a.slippage)
    Path(a.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
