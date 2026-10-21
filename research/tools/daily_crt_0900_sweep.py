#!/usr/bin/env python3
"""Parameter sweep for 09:00 CRT-style XAUUSD liquidity-sweep setups.

Exploratory only. Session is configured as 09:00 SAST (07:00 UTC, UTC+2);
broker timezone is not inferred. Uses derived M5 bars, not quote-level fills.
"""
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
from offline_tick_replay import ARCHIVE, EXPECTED, sha, load, bars

OUT = Path("research-output")
OUT.mkdir(exist_ok=True)
SESSION_HOUR_UTC = int(os.getenv("CRT_SESSION_HOUR_UTC", "7"))
WINDOW_MINUTES = int(os.getenv("CRT_WINDOW_MINUTES", "120"))
SPREAD_CAP = float(os.getenv("CRT_SPREAD_CAP", "0.80"))
SLIPPAGE_ROUND_TRIP = 0.70


def build_signals(b, range_kind, confirmation):
    x = b.copy()
    x["atr"] = pd.concat([
        x.high-x.low, (x.high-x.close.shift()).abs(),
        (x.low-x.close.shift()).abs()
    ], axis=1).max(axis=1).ewm(alpha=1/14, adjust=False).mean()
    x["day"] = x.index.floor("D")
    out = []
    for i in range(30, len(x)-1):
        t=x.index[i]; r=x.iloc[i]
        if t.hour*60+t.minute < SESSION_HOUR_UTC*60:
            continue
        if t.hour*60+t.minute >= SESSION_HOUR_UTC*60+WINDOW_MINUTES:
            continue
        day=t.floor("D")
        if range_kind == "previous_day":
            prior=x.loc[(x.index>=day-pd.Timedelta(days=1))&(x.index<day)]
            if prior.empty: continue
            hi=float(prior.high.max()); lo=float(prior.low.min())
        else:
            start=day+pd.Timedelta(hours=SESSION_HOUR_UTC)-pd.Timedelta(hours=7)
            # Range is midnight to session start UTC, not including current bar.
            prior=x.loc[(x.index>=day)&(x.index<day+pd.Timedelta(hours=SESSION_HOUR_UTC))]
            if prior.empty: continue
            hi=float(prior.high.max()); lo=float(prior.low.min())
        if not np.isfinite(r.atr) or r.atr<=0: continue
        if not np.isfinite(r.spread) or r.spread<0 or r.spread>SPREAD_CAP: continue
        # Reversal after a liquidity sweep: close must reclaim the reference range.
        short = r.high > hi and r.close < hi and r.close < r.open
        long = r.low < lo and r.close > lo and r.close > r.open
        if confirmation in ("structure", "displacement", "displacement_fvg"):
            # Require a close beyond the previous completed M5 candle's opposing extreme.
            prev=x.iloc[i-1]
            short = short and r.close < prev.low
            long = long and r.close > prev.high
        if confirmation in ("displacement", "displacement_fvg"):
            body=abs(float(r.close-r.open))
            short = short and body >= 0.5*float(r.atr)
            long = long and body >= 0.5*float(r.atr)
        if confirmation == "displacement_fvg":
            # Causal three-bar imbalance confirmation, formed no later than signal close.
            older=x.iloc[i-2]
            short = short and r.high < older.low
            long = long and r.low > older.high
        if short or long:
            side=-1 if short else 1
            out.append({"i":i,"time":t,"side":side,"sweep_high":float(r.high),
                        "sweep_low":float(r.low),"atr":float(r.atr),
                        "entry_i":i+1,"range_kind":range_kind,
                        "confirmation":confirmation})
    return out


def simulate(x, sigs, target_r, buffer_atr):
    trades=[]; last_exit=-1
    for s in sigs:
        i=s["i"]; ei=s["entry_i"]
        if i <= last_exit or ei>=len(x): continue
        entry=float(x.open.iloc[ei]); spread_in=float(x.spread_open.iloc[ei])
        if not np.isfinite(spread_in) or spread_in>SPREAD_CAP: continue
        side=s["side"]; atr=s["atr"]
        if side==1:
            sl=s["sweep_low"]-buffer_atr*atr
            risk=entry-sl
            tp=entry+target_r*risk
        else:
            sl=s["sweep_high"]+buffer_atr*atr
            risk=sl-entry
            tp=entry-target_r*risk
        if risk<=0: continue
        exit_price=None; reason="END_OF_DATA_MARK"; ex_i=len(x)-1
        for j in range(ei,len(x)):
            bar=x.iloc[j]
            if side==1:
                hit_sl=bar.low<=sl; hit_tp=bar.high>=tp
            else:
                hit_sl=bar.high>=sl; hit_tp=bar.low<=tp
            if hit_sl or hit_tp:
                # Conservative ordering when both levels occur in one M5 bar.
                if hit_sl:
                    exit_price=sl; reason="SL"
                else:
                    exit_price=tp; reason="TP"
                ex_i=j; break
        if exit_price is None:
            exit_price=float(x.close.iloc[-1])
        exit_spread=float(x.spread_max.iloc[ex_i])
        gross=(exit_price-entry)*side
        cost=.5*(spread_in+exit_spread)+SLIPPAGE_ROUND_TRIP
        net=gross-cost
        trades.append({"entry_time":str(x.index[ei]),"exit_time":str(x.index[ex_i]),
                       "side":"LONG" if side==1 else "SHORT","net_price_units":net,
                       "gross_price_units":gross,"cost_price_units":cost,"reason":reason,
                       "target_r":target_r,"buffer_atr":buffer_atr,
                       "range_kind":s["range_kind"],"confirmation":s["confirmation"]})
        last_exit=ex_i
    return trades


def metrics(trades):
    d=pd.DataFrame(trades)
    if d.empty: return {"trades":0,"net":0.0,"pf":None,"win_rate_pct":None,"max_dd":0.0}
    n=d.net_price_units
    wins=float(n[n>0].sum()); losses=float(-n[n<0].sum())
    eq=n.cumsum()
    return {"trades":int(len(d)),"net":round(float(n.sum()),4),
            "pf":round(wins/losses,4) if losses else (None if not wins else "INF"),
            "win_rate_pct":round(float((n>0).mean()*100),2),
            "max_dd":round(float((eq.cummax()-eq).max()),4)}


def main():
    if not ARCHIVE.exists(): raise FileNotFoundError(str(ARCHIVE))
    actual=sha(ARCHIVE)
    if EXPECTED and actual!=EXPECTED: raise RuntimeError("archive SHA-256 mismatch")
    ticks,_=load()
    ticks=ticks[(ticks.ask>=ticks.bid)&(ticks.bid>0)&(ticks.ask>0)].drop_duplicates(["timestamp","bid","ask"])
    b=bars(ticks)
    split=b.index[int(len(b)*.7)]
    rows=[]; ledgers=[]
    for rng in ("previous_day","pre_0900"):
      for conf in ("reclaim","structure","displacement","displacement_fvg"):
       sigs=build_signals(b,rng,conf)
       for target in (1.5,2.0,3.0):
        for buffer in (0.0,0.1):
         trades=simulate(b,sigs,target,buffer)
         if not trades:
          rows.append({"range":rng,"confirmation":conf,"target_r":target,"buffer_atr":buffer,
                       "all":metrics([]),"oos":metrics([]),"status":"NO_TRADES"})
          continue
         d=pd.DataFrame(trades)
         dates=pd.to_datetime(d.entry_time,utc=True)
         allm=metrics(trades); oos=metrics(d.loc[dates>=split].to_dict("records"))
         status="BLOCKED_INSUFFICIENT_EVIDENCE"
         if oos["trades"]>=30 and oos["pf"] is not None and isinstance(oos["pf"],(int,float)) and oos["pf"]>=1.1 and oos["net"]>0 and allm["trades"]>=100 and isinstance(allm["pf"],(int,float)) and allm["pf"]>=1.2:
          status="PASS_EXPLORATORY_GATES"
         rows.append({"range":rng,"confirmation":conf,"target_r":target,"buffer_atr":buffer,
                      "all":allm,"oos":oos,"status":status})
         for tr in trades:
          tr.update({"target_r":target,"buffer_atr":buffer})
          ledgers.append(tr)
    rows.sort(key=lambda z: (z["status"]=="PASS_EXPLORATORY_GATES",
       (z.get("oos") or {}).get("pf") if isinstance((z.get("oos") or {}).get("pf"),(int,float)) else -1,
       (z.get("oos") or {}).get("net",0)),reverse=True)
    report={"archive_sha256":actual,"provenance":"third-party Dukascopy, not PXBT-native",
      "session_definition":{"local_label":"09:00 SAST","assumed_utc_hour":SESSION_HOUR_UTC,
      "window_minutes":WINDOW_MINUTES,"warning":"verify historical SAST and broker server time"},
      "bars":len(b),"split_utc":split.isoformat(),"variants_tested":len(rows),
      "limitations":["derived M5 OHLC, not quote-level fills","stop-first when stop and target touched in same bar",
      "entry at next bar open; exit spread is maximum in exit bar","commission and swap not modelled",
      "short sample unsuitable for final strategy selection"],"ranked_results":rows}
    (OUT/"daily_crt_0900_sweep.json").write_text(json.dumps(report,indent=2))
    if ledgers: pd.DataFrame(ledgers).to_csv(OUT/"daily_crt_0900_trade_ledger.csv",index=False)
    print(json.dumps({"variants_tested":len(rows),"top_10":rows[:10],
      "pass_count":sum(r["status"]=="PASS_EXPLORATORY_GATES" for r in rows),
      "report":"research-output/daily_crt_0900_sweep.json"},indent=2))
if __name__=="__main__": main()
