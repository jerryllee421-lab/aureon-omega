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
 raw=lzma.decompress(raw)
 if len(raw)%20: raise ValueError("Invalid BI5 record size in "+name)
 parts=pathlib.Path(name).parts
 nums=[int("".join(c for c in p if c.isdigit())) for p in parts if any(c.isdigit() for c in p)]
 if len(nums)<4: raise ValueError("Cannot infer date/hour from "+name)
 y,mo,day,hour=nums[-4:]; base=pd.Timestamp(year=y,month=mo,day=day,hour=hour,tz="UTC")
 rows=[]
 for off in range(0,len(raw),20):
  ms,ask,bid,av,bv=struct.unpack(">IIIff",raw[off:off+20])
  rows.append((base+pd.Timedelta(milliseconds=ms),bid*1e-5,ask*1e-5))
 return pd.DataFrame(rows,columns=["timestamp","bid","ask"])
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
      ts=d[tc]
      if str(c[tc]).lower().endswith("_msc") or str(c[tc]).lower().endswith("_ms") or str(c[tc]).lower()=="timestamp_ms":
       ts=pd.to_datetime(ts,unit="ms",utc=True,errors="coerce")
      else: ts=pd.to_datetime(ts,utc=True,errors="coerce")
      frames.append(pd.DataFrame({"timestamp":ts,"bid":pd.to_numeric(d[bc],errors="coerce"),"ask":pd.to_numeric(d[ac],errors="coerce")}))
     else: members[-1]["columns"]=list(d.columns); members[-1]["unsupported_schema"]=True
    except Exception as e: members[-1]["parse_error"]=str(e)
 if not frames: raise RuntimeError("No supported CSV or BI5 bid/ask tick data found. See archive member listing.")
 ticks=pd.concat(frames,ignore_index=True).dropna().sort_values("timestamp").reset_index(drop=True)
 return ticks,members
def bars(t):
 d=t.set_index("timestamp"); m=((d.bid+d.ask)/2)
 b=m.resample("5min").ohlc()
 b["spread"]=d.assign(s=d.ask-d.bid).s.resample("5min").mean()
 b["tick_volume"]=d.bid.resample("5min").count()
 return b.dropna()
def replay(b,name,split):
 x=b.copy(); c=x.close
 x["ema"]=c.ewm(span=20,adjust=False).mean()
 delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
 x["rsi"]=100-100/(1+up/dn.replace(0,np.nan))
 tr=pd.concat([x.high-x.low,(x.high-c.shift()).abs(),(x.low-c.shift()).abs()],axis=1).max(axis=1)
 x["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
 trades=[]; pos=None
 for i in range(25,len(x)-1):
  r=x.iloc[i]; t=x.index[i]
  if pos:
   ex=None; why=""
   if pos["side"]==1 and r.low<=pos["sl"]: ex=pos["sl"]; why="SL"
   elif pos["side"]==1 and r.high>=pos["tp"]: ex=pos["tp"]; why="TP"
   elif pos["side"]==-1 and r.high>=pos["sl"]: ex=pos["sl"]; why="SL"
   elif pos["side"]==-1 and r.low<=pos["tp"]: ex=pos["tp"]; why="TP"
   if ex is not None:
    gross=(ex-pos["entry"])*pos["side"]; net=gross-(float(pos["spread"])+float(r.spread))/2-2*0.35
    trades.append({"strategy":name,"entry_time":str(pos["time"]),"exit_time":str(t),"net_price_units":net,"gross_price_units":gross,"reason":why}); pos=None
  if pos or not np.isfinite(r.atr) or r.atr<=0 or not np.isfinite(r.rsi): continue
  if not np.isfinite(r.spread) or r.spread<0 or r.spread>0.80: continue
  side=0
  if name=="m5_mean_reversion":
   if r.close<r.ema-1.25*r.atr and r.rsi<=30 and r.close>r.open: side=1
   elif r.close>r.ema+1.25*r.atr and r.rsi>=70 and r.close<r.open: side=-1
  elif name=="h4_breakout":
   h=x.loc[x.index<t].resample("4h").agg({"high":"max","low":"min","close":"last"}).dropna()
   h=h.loc[(h.index+pd.Timedelta(hours=4))<=t]
   if len(h)>21:
    if h.close.iloc[-1]>h.high.iloc[-21:-1].max()+.1*r.atr: side=1
    elif h.close.iloc[-1]<h.low.iloc[-21:-1].min()-.1*r.atr: side=-1
  elif name=="session_breakout":
   day=t.floor("D"); rg=x.loc[(x.index>=day)&(x.index<day+pd.Timedelta(hours=7))]
   if 7<=t.hour<17 and len(rg):
    if r.close>rg.high.max()+.1*r.atr: side=1
    elif r.close<rg.low.min()-.1*r.atr: side=-1
  elif name=="daily_crt":
   d=x.loc[x.index<t.floor("D")].resample("1D").agg({"high":"max","low":"min","close":"last"}).dropna()
   if len(d):
    prev=d.iloc[-1]
    if r.low<prev.low and prev.low<r.close<prev.high and r.close>r.open: side=1
    elif r.high>prev.high and prev.low<r.close<prev.high and r.close<r.open: side=-1
  elif name=="session_vwap_ema":
   # Tick-volume-weighted M5 typical-price VWAP proxy, reset at UTC day boundary.
   day=t.floor("D")
   sess=x.loc[(x.index>=day)&(x.index<=t)]
   vol=sess.tick_volume.clip(lower=0)
   denom=float(vol.sum())
   if denom>0:
    vwap=float((((sess.high+sess.low+sess.close)/3.0)*vol).sum()/denom)
    prev=x.iloc[i-1]
    if r.close>vwap and r.close>r.ema and prev.close<=prev.ema: side=1
    elif r.close<vwap and r.close<r.ema and prev.close>=prev.ema: side=-1
  if side:
   entry=float(x.open.iloc[i+1]); stop=1.5*float(r.atr)
   pos={"side":side,"entry":entry,"spread":float(x.spread.iloc[i+1]),"sl":entry-side*stop,"tp":entry+side*stop*1.5,"time":x.index[i+1]}
 if pos:
  r=x.iloc[-1]; gross=(float(r.close)-pos["entry"])*pos["side"]; trades.append({"strategy":name,"entry_time":str(pos["time"]),"exit_time":str(x.index[-1]),"net_price_units":gross-(float(pos["spread"])+float(r.spread))/2-0.70,"gross_price_units":gross,"reason":"END_OF_DATA_MARK"})
 td=pd.DataFrame(trades)
 if td.empty: return {"strategy":name,"trade_count":0,"note":"No trades; no performance conclusion"},td
 def met(d):
  wins=d.loc[d.net_price_units>0,"net_price_units"].sum(); losses=-d.loc[d.net_price_units<0,"net_price_units"].sum()
  eq=d.net_price_units.cumsum(); dd=(eq.cummax()-eq).max()
  return {"trade_count":int(len(d)),"net_price_units":float(d.net_price_units.sum()),"profit_factor":float(wins/losses) if losses>0 else None,"win_rate_pct":float((d.net_price_units>0).mean()*100),"max_trade_sequence_drawdown_price_units":float(dd),"average_net_price_units":float(d.net_price_units.mean())}
 dates=pd.to_datetime(td.entry_time,utc=True)
 result={"strategy":name,"all":met(td),"in_sample":met(td[dates<split]),"out_of_sample":met(td[dates>=split]),"cost_assumptions":{"slippage_per_side_price_units":.35,"spread_cap_price_units":.80,"commission":0,"spread_cost":"half entry spread plus half exit spread; entry prices are mid-price to avoid double-counting"},"limitations":["price-unit P/L only; contract sizing/account-currency conversion not modelled","bar-based stop/target sequencing is conservative approximation, not tick-by-tick MT5 execution","session uses UTC; broker timezone/DST unverified","Offline VWAP uses tick-count-weighted M5 typical price; this is a tick-volume proxy, not exchange volume, and resets at UTC midnight"]}
 return result,td
def main():
 if not ARCHIVE.exists(): raise FileNotFoundError("Tick archive missing: "+str(ARCHIVE))
 actual=sha(ARCHIVE)
 if EXPECTED and actual!=EXPECTED: raise RuntimeError("SHA-256 mismatch; refusing to process")
 ticks,members=load(); spread=ticks.ask-ticks.bid
 bad=int((spread<0).sum()); dup=int(ticks.duplicated(["timestamp","bid","ask"]).sum())
 gaps=ticks.timestamp.diff().dt.total_seconds()
 report={"archive":str(ARCHIVE),"sha256":actual,"sha256_verified":actual==EXPECTED,"files":members,"member_count":len(members),
 "tick_rows_raw":int(len(ticks)),"start_utc":ticks.timestamp.min().isoformat(),"end_utc":ticks.timestamp.max().isoformat(),
 "negative_spread_rows":bad,"duplicate_quote_rows":dup,"zero_spread_rows":int((spread==0).sum()),
 "spread_price_units":{"median":float(spread.median()),"p95":float(spread.quantile(.95)),"max":float(spread.max())},
 "gap_seconds":{"p50":float(gaps.quantile(.5)),"p95":float(gaps.quantile(.95)),"max":float(gaps.max())},
 "provenance":"Third-party Dukascopy archive, not verified PXBT broker-native ticks","trading_performed":False,"warnings":[]}
 ticks=ticks[(ticks.ask>=ticks.bid)&(ticks.bid>0)&(ticks.ask>0)].drop_duplicates(["timestamp","bid","ask"]).reset_index(drop=True)
 b=bars(ticks)
 if len(b)<100: raise RuntimeError("Insufficient M5 bars: "+str(len(b)))
 split=b.index[int(len(b)*.7)]; report["m5_bars"]=int(len(b)); report["train_oos_split_utc"]=split.isoformat()
 ledgers=[]; results=[]
 for name in ("m5_mean_reversion","h4_breakout","session_breakout","daily_crt","session_vwap_ema"):
  res,td=replay(b,name,split); results.append(res)
  if len(td): ledgers.append(td)
 report["strategy_results"]=results
 if bad: report["warnings"].append("Negative spread rows were found.")
 if dup: report["warnings"].append("Duplicate quotes found; duplicate rows removed for replay.")
 if ledgers: pd.concat(ledgers,ignore_index=True).to_csv(OUT/"trades.csv",index=False)
 (OUT/"tick_audit_and_replay.json").write_text(json.dumps(report,indent=2,default=str))
 (OUT/"tick_audit_and_replay.md").write_text("# AUREON Offline Tick Audit and Replay\n\n"+json.dumps(report,indent=2,default=str))
 print(json.dumps({"tick_rows":report["tick_rows_raw"],"m5_bars":report["m5_bars"],"sha256_verified":report["sha256_verified"],"results":results,"warnings":report["warnings"]},indent=2))
if __name__=="__main__": main()
