#!/usr/bin/env python3
"""Offline XAUUSD tick archive audit and basic tick-derived strategy replay."""
import os, json, hashlib, zipfile, pathlib, lzma, struct
import numpy as np
import pandas as pd

ARCHIVE=pathlib.Path(os.getenv("TICK_ARCHIVE","xauusd-ticks-2026-10.zip"))
EXPECTED=os.getenv("EXPECTED_SHA256","d354c8769bd4d6f6c5a57a7da87843acdddec4f03815137b339c6ed5786069b0")
OUT=pathlib.Path("research-output"); OUT.mkdir(exist_ok=True)
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def decode_bi5(raw,name):
 scale=os.getenv('BI5_PRICE_SCALE')
 if not scale:
  raise ValueError('BI5 price scale is instrument-specific; set BI5_PRICE_SCALE explicitly after verifying archive metadata')
 scale=float(scale)
 if not np.isfinite(scale) or scale<=0:
  raise ValueError('BI5_PRICE_SCALE must be positive and finite')
 raw=lzma.decompress(raw)
 if len(raw)%20: raise ValueError("Invalid BI5 record size in "+name)
 parts=pathlib.Path(name).parts
 nums=[int("".join(c for c in p if c.isdigit())) for p in parts if any(c.isdigit() for c in p)]
 if len(nums)<4: raise ValueError("Cannot infer date/hour from "+name)
 y,mo,day,hour=nums[-4:]; base=pd.Timestamp(year=y,month=mo,day=day,hour=hour,tz="UTC")
 rows=[]
 for off in range(0,len(raw),20):
  ms,ask,bid,av,bv=struct.unpack(">IIIff",raw[off:off+20])
  rows.append((base+pd.Timedelta(milliseconds=ms),bid*scale,ask*scale))
 return pd.DataFrame(rows,columns=["timestamp","bid","ask"])
def parse_timestamp(series, column_name):
 """Parse timestamps without silently interpreting epoch seconds as nanoseconds."""
 name=str(column_name).lower()
 if name.endswith("_msc") or name.endswith("_ms") or name=="timestamp_ms":
  return pd.to_datetime(series,unit="ms",utc=True,errors="coerce")
 if pd.api.types.is_numeric_dtype(series):
  vals=pd.to_numeric(series,errors="coerce").dropna()
  if vals.empty:
   return pd.to_datetime(series,utc=True,errors="coerce")
  magnitude=float(vals.abs().median())
  if magnitude>=1e17: unit="ns"
  elif magnitude>=1e14: unit="us"
  elif magnitude>=1e11: unit="ms"
  elif magnitude>=1e8: unit="s"
  else:
   raise ValueError("Ambiguous numeric timestamp scale; provide an explicit *_ms or datetime column")
  return pd.to_datetime(series,unit=unit,utc=True,errors="coerce")
 return pd.to_datetime(series,utc=True,errors="coerce")

def load():
 frames=[]; members=[]
 with zipfile.ZipFile(ARCHIVE) as z:
  for info in z.infolist():
   if info.is_dir(): continue
   members.append({"name":info.filename,"size_bytes":info.file_size,"crc32":format(info.CRC,"08x")})
   ext=pathlib.Path(info.filename).suffix.lower()
   if ext==".bi5":
    try: frames.append(decode_bi5(z.read(info),info.filename))
    except Exception as e: members[-1]["parse_error"]=str(e)
   elif ext in (".csv",".parquet"):
    try:
     d=pd.read_csv(z.open(info)) if ext==".csv" else pd.read_parquet(z.open(info))
     c={str(x).lower().strip():x for x in d.columns}
     tc=next((c[k] for k in ("timestamp","time","datetime","date","utc time","gmt time","time_msc","timestamp_ms","ts","t") if k in c),None)
     bc=next((c[k] for k in ("bid","bid_price","bidprice","bidprice","b") if k in c),None)
     ac=next((c[k] for k in ("ask","ask_price","askprice","a") if k in c),None)
     if tc and bc and ac:
      ts=parse_timestamp(d[tc],c[tc])
      frames.append(pd.DataFrame({"timestamp":ts,"bid":pd.to_numeric(d[bc],errors="coerce"),"ask":pd.to_numeric(d[ac],errors="coerce")}))
     else: members[-1]["columns"]=list(d.columns); members[-1]["unsupported_schema"]=True
    except Exception as e: members[-1]["parse_error"]=str(e)
 if not frames: raise RuntimeError("No supported CSV or BI5 bid/ask tick data found. See archive member listing.")
 ticks=pd.concat(frames,ignore_index=True).dropna().sort_values("timestamp").reset_index(drop=True)
 return ticks,members
def bars(t):
 d=t.set_index("timestamp"); m=((d.bid+d.ask)/2)
 b=m.resample("5min").ohlc()
 spread=d.assign(s=d.ask-d.bid).s
 b["spread"]=spread.resample("5min").mean()
 b["spread_open"]=spread.resample("5min").first()
 b["spread_max"]=spread.resample("5min").max()
 b["tick_volume"]=d.bid.resample("5min").count()
 return b.dropna()
def replay(b,name,split):
 """Exploratory replay with closed-bar signals, conservative intrabar exits and explicit limitations.
 This remains a bar replay, not MT5 native real-tick execution.
 """
 x=b.copy(); c=x.close
 x["ema"]=c.ewm(span=20,adjust=False).mean()
 delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
 x["rsi"]=100-100/(1+up/dn.replace(0,np.nan))
 tr=pd.concat([x.high-x.low,(x.high-c.shift()).abs(),(x.low-c.shift()).abs()],axis=1).max(axis=1)
 x["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
 x["adx"]=np.nan
 raw_plus_dm=x.high.diff()
 raw_minus_dm=-x.low.diff()
 # Compare raw directional moves before masking either series. Mutating +DM first
 # would otherwise change the condition used to calculate -DM and bias ADX.
 plus_dm=raw_plus_dm.where((raw_plus_dm>raw_minus_dm)&(raw_plus_dm>0),0.0)
 minus_dm=raw_minus_dm.where((raw_minus_dm>raw_plus_dm)&(raw_minus_dm>0),0.0)
 atr_wilder=tr.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan)
 pdi=100*plus_dm.ewm(alpha=1/14,adjust=False).mean()/atr_wilder
 mdi=100*minus_dm.ewm(alpha=1/14,adjust=False).mean()/atr_wilder
 dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
 x["adx"]=dx.ewm(alpha=1/14,adjust=False).mean()
 # Construct fully closed HTF bars once. Their availability timestamp is the bar close.
 h4=x.resample("4h",label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
 h4.index=h4.index+pd.Timedelta(hours=4)
 h1=x.resample("1h",label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
 h1.index=h1.index+pd.Timedelta(hours=1)
 d1=x.resample("1D",label="left",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
 d1.index=d1.index+pd.Timedelta(days=1)
 d1["ema20"]=d1.close.ewm(span=20,adjust=False).mean()
 d1["ema50"]=d1.close.ewm(span=50,adjust=False).mean()
 trades=[]; pos=None; last_exit_i=-10**9; last_entry_time=None
 for i in range(30,len(x)-1):
  r=x.iloc[i]; t=x.index[i]
  if pos:
   # A stop is assumed before target when both occur in the same bar.
   ex=None; why=""
   if pos["side"]==1 and r.low<=pos["sl"]: ex=pos["sl"]; why="SL"
   elif pos["side"]==1 and r.high>=pos["tp"]: ex=pos["tp"]; why="TP"
   elif pos["side"]==-1 and r.high>=pos["sl"]: ex=pos["sl"]; why="SL"
   elif pos["side"]==-1 and r.low<=pos["tp"]: ex=pos["tp"]; why="TP"
   if ex is not None:
    gross=(ex-pos["entry"])*pos["side"]
    # Mid-price entry/exit, so charge full quoted spread + two-sided slippage.
    # Exit spread uses the full exit bar's maximum as a conservative cost bound;
    # exact exit-time spread requires tick-level fill simulation.
    cost=0.5*(float(pos["entry_spread"])+float(r.spread_max))+0.70
    trades.append({"strategy":name,"entry_time":str(pos["time"]),"exit_time":str(t),"net_price_units":gross-cost,"gross_price_units":gross,"cost_price_units":cost,"reason":why})
    pos=None; last_exit_i=i
  if pos or i-last_exit_i<6 or not np.isfinite(r.atr) or r.atr<=0 or not np.isfinite(r.rsi): continue
  if not np.isfinite(r.spread) or r.spread<0 or r.spread>0.80: continue
  side=0
  if name=="m5_mean_reversion":
   if not np.isfinite(r.adx) or r.adx>25: continue
   if r.close<r.ema-1.25*r.atr and r.rsi<=30 and r.close>r.open: side=1
   elif r.close>r.ema+1.25*r.atr and r.rsi>=70 and r.close<r.open: side=-1
  elif name=="h4_breakout":
   avail=h4.loc[h4.index<=t]
   if len(avail)>20:
    cur=avail.iloc[-1]; prior=avail.iloc[-21:-1]
    if cur.close>prior.high.max()+.1*r.atr: side=1
    elif cur.close<prior.low.min()-.1*r.atr: side=-1
  elif name=="session_breakout":
   # UTC session proxy only; must be aligned to verified broker server time before promotion.
   day=t.floor("D"); rg=x.loc[(x.index>=day)&(x.index<day+pd.Timedelta(hours=7))]
   if 7<=t.hour<17 and len(rg):
    if r.close>rg.high.max()+.1*r.atr: side=1
    elif r.close<rg.low.min()-.1*r.atr: side=-1
  elif name=="daily_crt":
   avail=d1.loc[d1.index<=t]
   if len(avail):
    prev=avail.iloc[-1]
    if r.low<prev.low and prev.low<r.close<prev.high and r.close>r.open: side=1
    elif r.high>prev.high and prev.low<r.close<prev.high and r.close<r.open: side=-1
  elif name=="h1_breakout":
   avail=h1.loc[h1.index<=t]
   if len(avail)>20:
    cur=avail.iloc[-1]; prior=avail.iloc[-21:-1]
    if cur.close>prior.high.max()+.1*r.atr: side=1
    elif cur.close<prior.low.min()-.1*r.atr: side=-1
  elif name=="amd_session":
   # UTC proxy: accumulation 00:00-06:00; trade sweep/reclaim during 07:00-16:00.
   day=t.floor("D")
   acc=x.loc[(x.index>=day)&(x.index<day+pd.Timedelta(hours=6))]
   if 7<=t.hour<16 and len(acc):
    ahi=float(acc.high.max()); alo=float(acc.low.min())
    if r.low<alo and r.close>alo and r.close>r.open: side=1
    elif r.high>ahi and r.close<ahi and r.close<r.open: side=-1
  elif name=="fvg_scalper":
   # Three-candle imbalance, then closed-bar rejection into the gap; no future bars used.
   if i>=3:
    older=x.iloc[i-3]
    formed=x.iloc[i-1]
    if formed.low>older.high:
     gap_lo=float(older.high); gap_hi=float(formed.low)
     if r.low<=gap_hi and r.close>=(gap_lo+gap_hi)/2 and r.close>r.open: side=1
    elif formed.high<older.low:
     gap_lo=float(formed.high); gap_hi=float(older.low)
     if r.high>=gap_lo and r.close<=(gap_lo+gap_hi)/2 and r.close<r.open: side=-1
  elif name=="gold_trap":
   # False break of the prior 12 completed M5 bars; requires close back inside the range.
   prior=x.iloc[i-12:i]
   if len(prior)==12:
    hi=float(prior.high.max()); lo=float(prior.low.min())
    upper_wick=float(r.high-max(r.open,r.close))
    lower_wick=float(min(r.open,r.close)-r.low)
    if r.high>hi and r.close<hi and upper_wick>=.20*r.atr and r.close<r.open: side=-1
    elif r.low<lo and r.close>lo and lower_wick>=.20*r.atr and r.close>r.open: side=1
  elif name=="daily_swing":
   avail=d1.loc[d1.index<=t]
   if len(avail)>=50:
    d=avail.iloc[-1]
    prev=x.iloc[i-1]
    if d.close>d.ema20 and d.ema20>d.ema50 and prev.close<=prev.ema and r.close>r.ema: side=1
    elif d.close<d.ema20 and d.ema20<d.ema50 and prev.close>=prev.ema and r.close<r.ema: side=-1
  elif name=="session_vwap_ema":
   day=t.floor("D"); sess=x.loc[(x.index>=day)&(x.index<=t)]
   vol=sess.tick_volume.clip(lower=0); denom=float(vol.sum())
   if denom>0:
    vwap=float((((sess.high+sess.low+sess.close)/3.0)*vol).sum()/denom)
    prev=x.iloc[i-1]
    if r.close>vwap and r.close>r.ema and prev.close<=prev.ema: side=1
    elif r.close<vwap and r.close<r.ema and prev.close>=prev.ema: side=-1
  if side:
   # Entry is next bar midpoint; costs are charged separately once at entry and exit.
   entry=float(x.open.iloc[i+1]); entry_spread=float(x.spread_open.iloc[i+1])
   # Entry spread is known from the first quote of the entry bar, not its future average.
   if not np.isfinite(entry_spread) or entry_spread<0 or entry_spread>0.80: continue
   stop=1.5*float(r.atr)
   pos={"side":side,"entry":entry,"entry_spread":entry_spread,"sl":entry-side*stop,"tp":entry+side*stop*1.5,"time":x.index[i+1]}
 if pos:
  r=x.iloc[-1]; gross=(float(r.close)-pos["entry"])*pos["side"]
  cost=0.5*(float(pos["entry_spread"])+float(r.spread_max))+0.70
  trades.append({"strategy":name,"entry_time":str(pos["time"]),"exit_time":str(x.index[-1]),"net_price_units":gross-cost,"gross_price_units":gross,"cost_price_units":cost,"reason":"END_OF_DATA_MARK"})
 td=pd.DataFrame(trades)
 if td.empty: return {"strategy":name,"trade_count":0,"note":"No trades; no performance conclusion"},td
 def met(d):
  wins=d.loc[d.net_price_units>0,"net_price_units"].sum(); losses=-d.loc[d.net_price_units<0,"net_price_units"].sum()
  eq=d.net_price_units.cumsum(); dd=(eq.cummax()-eq).max()
  return {"trade_count":int(len(d)),"net_price_units":float(d.net_price_units.sum()),"profit_factor":float(wins/losses) if losses>0 else None,"win_rate_pct":float((d.net_price_units>0).mean()*100),"max_trade_sequence_drawdown_price_units":float(dd),"average_net_price_units":float(d.net_price_units.mean())}
 dates=pd.to_datetime(td.entry_time,utc=True)
 return {"strategy":name,"all":met(td),"in_sample":met(td[dates<split]),"out_of_sample":met(td[dates>=split]),"cost_assumptions":{"slippage_per_side_price_units":0.35,"spread_cap_price_units":0.80,"commission":0,"spread_cost":"half of first-quote entry spread plus half of maximum spread in the exit bar (conservative bound); plus two-sided slippage (0.35 per side)"},"limitations":["price-unit P/L only; contract sizing/account-currency conversion not modelled","bar-based stop/target sequencing assumes stop first when both hit","session uses UTC; broker timezone/DST unverified","VWAP is M5 tick-count-weighted typical-price proxy, not exchange volume","synthetic M5 OHLC aggregation cannot establish true tick fill order","entry uses first quote spread; exit spread uses maximum spread in exit bar as conservative bound, not exact exit-time quote"]},td

def main():
 if not ARCHIVE.exists(): raise FileNotFoundError("Tick archive missing: "+str(ARCHIVE))
 actual=sha(ARCHIVE)
 if EXPECTED and actual!=EXPECTED: raise RuntimeError("SHA-256 mismatch; refusing to process")
 ticks,members=load(); spread=ticks.ask-ticks.bid
 bad=int((spread<0).sum()); dup=int(ticks.duplicated(["timestamp","bid","ask"]).sum())
 gaps=ticks.timestamp.diff().dt.total_seconds()
 gap_mask=gaps>60
 weekday_mask=ticks.timestamp.dt.dayofweek<5
 weekday_gaps=gaps[weekday_mask & (gaps.index>0)]
 weekday_gaps=weekday_gaps[weekday_gaps<86400]
 spread_gt_080=int((spread>0.80).sum())
 spread_gt_2=int((spread>2.0).sum())
 report={"archive":str(ARCHIVE),"sha256":actual,"sha256_verified":actual==EXPECTED,"files":members,"member_count":len(members),
 "tick_rows_raw":int(len(ticks)),"start_utc":ticks.timestamp.min().isoformat(),"end_utc":ticks.timestamp.max().isoformat(),
 "negative_spread_rows":bad,"duplicate_quote_rows":dup,"zero_spread_rows":int((spread==0).sum()),
 "spread_price_units":{"median":float(spread.median()),"p95":float(spread.quantile(.95)),"max":float(spread.max()),
 "rows_over_0_80":spread_gt_080,"rows_over_2_00":spread_gt_2},
 "gap_seconds":{"p50":float(gaps.quantile(.5)),"p95":float(gaps.quantile(.95)),"max":float(gaps.max()),
 "gaps_over_60s":int(gap_mask.sum()),"gaps_over_5m":int((gaps>300).sum()),
 "weekday_gap_max_below_24h":float(weekday_gaps.max()) if len(weekday_gaps) else None},
 "provenance":"Third-party Dukascopy archive, not verified PXBT broker-native ticks","trading_performed":False,"warnings":[]}
 ticks=ticks[(ticks.ask>=ticks.bid)&(ticks.bid>0)&(ticks.ask>0)].drop_duplicates(["timestamp","bid","ask"]).reset_index(drop=True)
 b=bars(ticks)
 if len(b)<100: raise RuntimeError("Insufficient M5 bars: "+str(len(b)))
 split=b.index[int(len(b)*.7)]; report["m5_bars"]=int(len(b)); report["train_oos_split_utc"]=split.isoformat()
 ledgers=[]; results=[]
 for name in ("m5_mean_reversion","h4_breakout","h1_breakout","session_breakout","daily_crt","session_vwap_ema","amd_session","fvg_scalper","gold_trap","daily_swing"):
  res,td=replay(b,name,split); results.append(res)
  if len(td): ledgers.append(td)
 # Explicitly separate exploratory replay from strategy qualification.
 report["strategy_results"]=results
 # Cost stress replays identical trade decisions at 1.0x, 1.5x and 2.0x modeled costs.
 # This is sensitivity analysis, not a replacement for stressed execution/fill replay.
 if ledgers:
  ledger=pd.concat(ledgers,ignore_index=True)
  stress={}
  for strategy,group in ledger.groupby("strategy"):
   stress[strategy]={}
   for mult in (1.0,1.5,2.0):
    net=group["gross_price_units"]-group["cost_price_units"]*mult
    wins=float(net[net>0].sum()); losses=float(-net[net<0].sum())
    stress[strategy][f"{mult:.1f}x_cost"]={"trade_count":int(len(net)),"net_price_units":float(net.sum()),
     "profit_factor":float(wins/losses) if losses>0 else None,"win_rate_pct":float((net>0).mean()*100)}
  report["cost_stress_same_signals"]=stress
  # Fixed-parameter chronological stability folds; no fold is used to tune parameters.
  # Fold boundaries are equal-duration thirds of the full observed timestamp range.
  fold_start=ticks.timestamp.min()
  fold_end=ticks.timestamp.max()
  total_seconds=max((fold_end-fold_start).total_seconds(),1.0)
  fold_edges=[fold_start, fold_start+pd.Timedelta(seconds=total_seconds/3),
              fold_start+pd.Timedelta(seconds=2*total_seconds/3), fold_end+pd.Timedelta(microseconds=1)]
  fold_report={}
  for strategy,group in ledger.groupby("strategy"):
   group=group.copy()
   group["entry_dt"]=pd.to_datetime(group["entry_time"],utc=True)
   fold_report[strategy]=[]
   for fi in range(3):
    fg=group[(group.entry_dt>=fold_edges[fi])&(group.entry_dt<fold_edges[fi+1])]
    net=fg["net_price_units"]
    wins=float(net[net>0].sum()); losses=float(-net[net<0].sum())
    fold_report[strategy].append({"fold":fi+1,"start_utc":fold_edges[fi].isoformat(),
     "end_utc":fold_edges[fi+1].isoformat(),"trade_count":int(len(fg)),
     "net_price_units":float(net.sum()) if len(net) else 0.0,
     "profit_factor":float(wins/losses) if losses>0 else (None if wins==0 else "INF"),
     "win_rate_pct":float((net>0).mean()*100) if len(net) else None})
  report["fixed_parameter_chronological_folds"]=fold_report
 data_days=(ticks.timestamp.max()-ticks.timestamp.min()).total_seconds()/86400.0
 report["coverage_days_elapsed"]=float(data_days)
 report["qualification_policy"]={
  "minimum_closed_trades_all":100,
  "minimum_closed_trades_oos":30,
  "minimum_profit_factor_all_after_costs":1.20,
  "minimum_profit_factor_oos_after_costs":1.10,
  "requires_positive_oos_net":True,
  "requires_native_broker_tick_provenance":True,
  "requires_longer_multi_regime_sample":True,
  "requires_commission_swap_and_cost_stress_validation":True,
  "requires_native_mt5_every_tick_real_ticks_reproduction":True,
  "current_archive_is_native_broker_data":False
 }
 for res in results:
  allm=res.get("all",{})
  oosm=res.get("out_of_sample",{})
  reasons=[]
  if allm.get("trade_count",0)<100: reasons.append("fewer than 100 total trades")
  if oosm.get("trade_count",0)<30: reasons.append("fewer than 30 out-of-sample trades")
  if allm.get("profit_factor") is None or allm.get("profit_factor",0)<1.20: reasons.append("all-sample PF below 1.20")
  if oosm.get("profit_factor") is None or oosm.get("profit_factor",0)<1.10: reasons.append("out-of-sample PF below 1.10")
  if oosm.get("net_price_units",0)<=0: reasons.append("out-of-sample net result is not positive")
  reasons.append("data is third-party Dukascopy, not verified PXBT-native ticks")
  reasons.append("short sample; multi-regime walk-forward validation not yet established")
  reasons.append("commission/swap and execution-cost sensitivity not validated")
  reasons.append("native MT5 Every Tick Based on Real Ticks reproduction absent")
  res["qualification"]={"status":"BLOCKED_RESEARCH_ONLY","passed":False,"reasons":reasons}
 report["overall_qualification"]="NO_STRATEGY_QUALIFIED"
 report["overall_qualification_reason"]="No candidate passes the statistical gates, and the dataset provenance/coverage cannot qualify a strategy for deployment."
 if bad: report["warnings"].append("Negative spread rows were found.")
 if dup: report["warnings"].append("Duplicate quotes found; duplicate rows removed for replay.")
 if ledgers: pd.concat(ledgers,ignore_index=True).to_csv(OUT/"trades.csv",index=False)
 (OUT/"tick_audit_and_replay.json").write_text(json.dumps(report,indent=2,default=str))
 (OUT/"tick_audit_and_replay.md").write_text("# AUREON Offline Tick Audit and Replay\n\n"+json.dumps(report,indent=2,default=str))
 print(json.dumps({"tick_rows":report["tick_rows_raw"],"m5_bars":report["m5_bars"],"sha256_verified":report["sha256_verified"],"results":results,"warnings":report["warnings"]},indent=2))
if __name__=="__main__": main()
