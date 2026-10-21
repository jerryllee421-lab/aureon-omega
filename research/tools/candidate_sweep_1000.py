#!/usr/bin/env python3
"""Exploratory 1,000-candidate XAUUSD parameter sweep.
Uses the existing verified archive loader and M5 bar replay only. NOT native MT5 execution.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import offline_tick_replay as base

OUT = Path("research-output"); OUT.mkdir(exist_ok=True)
FAMILIES = [
 "M5 Mean Reversion","H4 Breakout","Session Breakout","Daily CRT","Session VWAP + EMA",
 "Liquidity Sweep + MSS","FVG Retracement","Trend Pullback","Opening Range Breakout","Volatility Expansion"
]
ENTRY_MODES = ["close confirmation","break-and-retest","sweep-and-reclaim","limit retracement","momentum confirmation"]
STOPS = [1.0,1.25,1.5,1.75,2.0]
RRS = [1.0,1.5,2.0,2.5]
RISKS = [0.10,0.25,0.50,0.75]
def indicators(b):
 x=b.copy(); c=x.close
 x["ema20"]=c.ewm(span=20,adjust=False).mean()
 x["ema50"]=c.ewm(span=50,adjust=False).mean()
 delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
 x["rsi"]=100-100/(1+up/dn.replace(0,np.nan))
 tr=pd.concat([x.high-x.low,(x.high-c.shift()).abs(),(x.low-c.shift()).abs()],axis=1).max(axis=1)
 x["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
 plus=x.high.diff(); minus=-x.low.diff()
 plus=plus.where((plus>minus)&(plus>0),0.0); minus=minus.where((minus>plus)&(minus>0),0.0)
 atr=x.atr.replace(0,np.nan); pdi=100*plus.ewm(alpha=1/14,adjust=False).mean()/atr; mdi=100*minus.ewm(alpha=1/14,adjust=False).mean()/atr
 x["adx"]=(100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)).ewm(alpha=1/14,adjust=False).mean()
 x["vol_med"]=x.tick_volume.rolling(20).median()
 x["atr_med"]=x.atr.rolling(20).median()
 x["vwap"]=np.nan
 for _, ix in pd.Series(np.arange(len(x)),index=x.index).groupby(x.index.floor("D")):
  ids=ix.values; vv=x.tick_volume.iloc[ids].clip(lower=0).to_numpy(); typ=((x.high+x.low+x.close)/3).iloc[ids].to_numpy()
  denom=np.cumsum(vv); num=np.cumsum(typ*vv)
  x.iloc[ids,x.columns.get_loc("vwap")]=np.divide(num,denom,out=np.full(len(ids),np.nan),where=denom>0)
 return x
def htf_levels(x):
 h4=x.resample("4h",label="left",closed="left").agg({"high":"max","low":"min","close":"last"}).dropna(); h4.index+=pd.Timedelta(hours=4)
 d1=x.resample("1D",label="left",closed="left").agg({"high":"max","low":"min","close":"last"}).dropna(); d1.index+=pd.Timedelta(days=1)
 return h4,d1
def signal(x,i,fam,entrymode):
 r=x.iloc[i]; p=x.iloc[i-1]; t=x.index[i]; atr=r.atr
 if not np.isfinite(atr) or atr<=0 or not np.isfinite(r.rsi): return 0
 # Entry variants change confirmation rather than pretending all are the same strategy.
 bull=r.close>r.open; bear=r.close<r.open
 if entrymode=="momentum confirmation": bull=bull and r.close>p.high; bear=bear and r.close<p.low
 if entrymode=="break-and-retest": bull=bull and r.low<=p.high and r.close>p.high; bear=bear and r.high>=p.low and r.close<p.low
 if entrymode=="limit retracement": bull=bull and r.low<=r.ema20 and r.close>r.ema20; bear=bear and r.high>=r.ema20 and r.close<r.ema20
 if fam=="M5 Mean Reversion":
  if r.adx>25: return 0
  return 1 if r.close<r.ema20-1.25*atr and r.rsi<=30 and bull else (-1 if r.close>r.ema20+1.25*atr and r.rsi>=70 and bear else 0)
 if fam=="H4 Breakout":
  prior=x.iloc[max(0,i-240):i]
  if len(prior)<40:return 0
  return 1 if r.close>prior.high.max()+.1*atr else (-1 if r.close<prior.low.min()-.1*atr else 0)
 if fam=="Session Breakout":
  day=t.floor("D"); rg=x.loc[(x.index>=day)&(x.index<day+pd.Timedelta(hours=7))]
  if not 7<=t.hour<17 or rg.empty:return 0
  return 1 if r.close>rg.high.max()+.1*atr else (-1 if r.close<rg.low.min()-.1*atr else 0)
 if fam=="Daily CRT":
  day=t.floor("D"); prev=x.loc[x.index<day]
  if prev.empty:return 0
  # Last fully completed daily candle, not today's partial data.
  pdaily=prev.resample("1D").agg({"high":"max","low":"min","close":"last"}).dropna()
  if pdaily.empty:return 0
  ph,pl=pdaily.high.iloc[-1],pdaily.low.iloc[-1]
  return 1 if r.low<pl and r.close>pl and r.close<ph and bull else (-1 if r.high>ph and r.close<ph and r.close>pl and bear else 0)
 if fam=="Session VWAP + EMA":
  return 1 if r.close>r.vwap and r.close>r.ema20 and p.close<=p.ema20 and bull else (-1 if r.close<r.vwap and r.close<r.ema20 and p.close>=p.ema20 and bear else 0)
 if fam=="Liquidity Sweep + MSS":
  w=x.iloc[max(0,i-12):i]
  if len(w)<8:return 0
  return 1 if r.low<w.low.min() and r.close>w.low.min() and r.close>p.high and bull else (-1 if r.high>w.high.max() and r.close<w.high.max() and r.close<p.low and bear else 0)
 if fam=="FVG Retracement":
  if i<3:return 0
  a=x.iloc[i-2]
  # Three-candle imbalance, entered only after current close returns to gap.
  return 1 if a.high<r.low and r.low<=r.close and bull else (-1 if a.low>r.high and r.high>=r.close and bear else 0)
 if fam=="Trend Pullback":
  return 1 if r.ema20>r.ema50 and r.low<=r.ema20 and r.close>r.ema20 and bull else (-1 if r.ema20<r.ema50 and r.high>=r.ema20 and r.close<r.ema20 and bear else 0)
 if fam=="Opening Range Breakout":
  day=t.floor("D"); rg=x.loc[(x.index>=day+pd.Timedelta(hours=13))&(x.index<day+pd.Timedelta(hours=14))]
  if t.hour<14 or t.hour>=18 or rg.empty:return 0
  return 1 if r.close>rg.high.max() and bull else (-1 if r.close<rg.low.min() and bear else 0)
 if fam=="Volatility Expansion":
  if not np.isfinite(r.atr_med) or r.atr_med<=0:return 0
  w=x.iloc[max(0,i-20):i]
  if len(w)<15 or r.atr_med>=w.atr.median():return 0
  return 1 if r.close>w.high.max() and bull else (-1 if r.close<w.low.min() and bear else 0)
 return 0
def evaluate(x, fam, entrymode, stopmult, rr, riskpct, split):
 trades=[]; pos=None; last_exit=-999
 # Conservative closed-bar replay. Signal on closed bar; fill at next bar open.
 for i in range(60,len(x)-1):
  r=x.iloc[i]; t=x.index[i]
  if pos:
   ex=None; reason=""
   if pos["side"]==1 and r.low<=pos["sl"]: ex=pos["sl"]; reason="SL"
   elif pos["side"]==1 and r.high>=pos["tp"]: ex=pos["tp"]; reason="TP"
   elif pos["side"]==-1 and r.high>=pos["sl"]: ex=pos["sl"]; reason="SL"
   elif pos["side"]==-1 and r.low<=pos["tp"]: ex=pos["tp"]; reason="TP"
   if ex is not None:
    gross=(ex-pos["entry"])*pos["side"]; cost=pos["entry_spread"]+float(r.spread)+.70
    net=gross-cost; trades.append({"entry_time":pos["time"].isoformat(),"exit_time":t.isoformat(),"gross_price_units":gross,"cost_price_units":cost,"net_price_units":net,"r_multiple":net/pos["risk_dist"],"exit_reason":reason})
    pos=None; last_exit=i
  if pos or i-last_exit<6 or not np.isfinite(r.spread) or r.spread<0 or r.spread>.80: continue
  # Simple regime/spread guard; reject high-spread bars and extreme ADX for mean reversion.
  side=signal(x,i,fam,entrymode)
  if side==0: continue
  if fam=="M5 Mean Reversion" and r.adx>25: continue
  if i+1>=len(x):continue
  entry=float(x.open.iloc[i+1]); es=float(x.spread.iloc[i+1]); dist=float(stopmult*r.atr)
  pos={"side":side,"entry":entry,"entry_spread":es,"sl":entry-side*dist,"tp":entry+side*dist*rr,"time":x.index[i+1],"risk_dist":dist,"risk_pct":riskpct}
 if pos:
  r=x.iloc[-1]; gross=(float(r.close)-pos["entry"])*pos["side"]; cost=pos["entry_spread"]+float(r.spread)+.70
  trades.append({"entry_time":pos["time"].isoformat(),"exit_time":x.index[-1].isoformat(),"gross_price_units":gross,"cost_price_units":cost,"net_price_units":gross-cost,"r_multiple":(gross-cost)/pos["risk_dist"],"exit_reason":"END_OF_DATA_MARK"})
 td=pd.DataFrame(trades)
 if td.empty:return {"trade_count":0,"note":"No closed trades; cannot rank"},td
 def met(d):
  wins=d.loc[d.net_price_units>0,"net_price_units"].sum(); losses=-d.loc[d.net_price_units<0,"net_price_units"].sum()
  eq=d.r_multiple.cumsum()*riskpct/100
  dd=(eq.cummax()-eq).max()
  return {"trade_count":int(len(d)),"net_price_units":float(d.net_price_units.sum()),"profit_factor":float(wins/losses) if losses>0 else None,"win_rate_pct":float((d.net_price_units>0).mean()*100),"avg_r":float(d.r_multiple.mean()),"risk_normalized_max_sequence_dd_pct":float(dd*100)}
 dates=pd.to_datetime(td.entry_time,utc=True)
 allm=met(td); ins=met(td[dates<split]); oos=met(td[dates>=split])
 return {"trade_count":len(td),"all":allm,"in_sample":ins,"out_of_sample":oos},td
def main():
 if not base.ARCHIVE.exists(): raise FileNotFoundError("Tick archive missing: "+str(base.ARCHIVE))
 actual=base.sha(base.ARCHIVE)
 if base.EXPECTED and actual!=base.EXPECTED: raise RuntimeError("Archive SHA mismatch; aborting")
 ticks,members=base.load(); raw=len(ticks)
 spread=ticks.ask-ticks.bid
 ticks=ticks[(ticks.ask>=ticks.bid)&(ticks.bid>0)&(ticks.ask>0)].drop_duplicates(["timestamp","bid","ask"]).reset_index(drop=True)
 b=base.bars(ticks)
 if len(b)<100: raise RuntimeError(f"Insufficient M5 bars: {len(b)}")
 x=indicators(b); split=x.index[int(len(x)*.7)]
 rows=[]; ledger=[]
 for fi,fam in enumerate(FAMILIES):
  for j in range(100):
   entrymode=ENTRY_MODES[j%5]; stopmult=STOPS[(j//5)%5]; rr=RRS[(j//25)%4]; risk=RISKS[(j//25)%4]
   cid=f"XAU-{fi*100+j+1:04d}"
   res,td=evaluate(x,fam,entrymode,stopmult,rr,risk,split)
   allm=res.get("all",{}); oos=res.get("out_of_sample",{})
   reasons=[]
   if res.get("trade_count",0)<100: reasons.append("fewer than 100 total trades")
   if oos.get("trade_count",0)<30: reasons.append("fewer than 30 OOS trades")
   if allm.get("profit_factor") is None or allm.get("profit_factor",0)<1.20: reasons.append("all-sample PF below 1.20")
   if oos.get("profit_factor") is None or oos.get("profit_factor",0)<1.10: reasons.append("OOS PF below 1.10")
   if oos.get("net_price_units",0)<=0: reasons.append("OOS net not positive")
   reasons += ["third-party Dukascopy data; not verified PXBT-native ticks","M5 bar replay; not native tick-by-tick fills","broker timezone, commission/swap and slippage model need validation","short sample; walk-forward and parameter robustness still required"]
   row={"candidate_id":cid,"strategy_family":fam,"entry_trigger":entrymode,"stop_atr_multiple":stopmult,"reward_risk":rr,"risk_percent":risk,"archive_sha256":actual,"tick_rows_raw":raw,"m5_bars":len(x),"train_oos_split_utc":split.isoformat(),**res,"qualification":{"status":"BLOCKED_RESEARCH_ONLY","passed":False,"reasons":reasons}}
   rows.append(row)
   if len(td):
    td=td.copy(); td.insert(0,"candidate_id",cid); td.insert(1,"strategy_family",fam); ledger.append(td)
 # Sort only for exploration; do not label winners or qualification.
 rows.sort(key=lambda z:(z.get("out_of_sample",{}).get("profit_factor") or 0,z.get("out_of_sample",{}).get("net_price_units",0)),reverse=True)
 pd.DataFrame([{k:v for k,v in r.items() if k not in ("all","in_sample","out_of_sample","qualification")} | {"all_metrics":json.dumps(r.get("all",{})),"in_sample_metrics":json.dumps(r.get("in_sample",{})),"out_of_sample_metrics":json.dumps(r.get("out_of_sample",{})),"qualification":json.dumps(r["qualification"])} for r in rows]).to_csv(OUT/"candidate_sweep_1000.csv",index=False)
 if ledger: pd.concat(ledger,ignore_index=True).to_csv(OUT/"candidate_sweep_trades.csv",index=False)
 report={"candidates_requested":1000,"candidates_executed":len(rows),"archive_sha256":actual,"archive_sha256_verified":actual==base.EXPECTED,"provenance":"Dukascopy third-party ticks; not verified PXBT-native data","raw_tick_rows":raw,"clean_tick_rows":len(ticks),"m5_bars":len(x),"start_utc":ticks.timestamp.min().isoformat(),"end_utc":ticks.timestamp.max().isoformat(),"split_utc":split.isoformat(),"qualification":"ALL BLOCKED pending native MT5 real-tick reproduction, longer sample, broker-cost validation and walk-forward robustness","top_20_exploratory":[{"candidate_id":r["candidate_id"],"family":r["strategy_family"],"PF_OOS":r.get("out_of_sample",{}).get("profit_factor"),"net_OOS_price_units":r.get("out_of_sample",{}).get("net_price_units"),"trades":r.get("trade_count"),"qualification":r["qualification"]["status"]} for r in rows[:20]],"warnings":["This is an exploratory M5 bar replay generated from tick quotes, not MT5 native Every Tick Based on Real Ticks.","All 1,000 candidates are kept BLOCKED_RESEARCH_ONLY regardless of rank.","Risk percentage is recorded and used for normalized R reporting; broker contract sizing/account currency is not modelled.","The generated configurations are 10 strategy families x 100 parameter variants, not 1,000 independently authored EAs."]}
 (OUT/"candidate_sweep_1000.json").write_text(json.dumps(report,indent=2))
 (OUT/"candidate_sweep_1000.md").write_text("# AUREON Ω — 1,000 Candidate Sweep\n\n"+json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=="__main__": main()
