#!/usr/bin/env python3
"""Daily CRT focused 1,000-configuration robustness sweep. Exploratory M5 bar replay only."""
import itertools, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import offline_tick_replay as base

OUT=Path("research-output"); OUT.mkdir(exist_ok=True)
EXPECTED_COUNT=1000
def prepare(b):
    x=b.copy(); c=x.close
    x["ema20"]=c.ewm(span=20,adjust=False).mean()
    x["ema50"]=c.ewm(span=50,adjust=False).mean()
    tr=pd.concat([x.high-x.low,(x.high-c.shift()).abs(),(x.low-c.shift()).abs()],axis=1).max(axis=1)
    x["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
    plus=x.high.diff(); minus=-x.low.diff()
    pdm=plus.where((plus>minus)&(plus>0),0.0); mdm=minus.where((minus>plus)&(minus>0),0.0)
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/x["atr"].replace(0,np.nan)
    mdi=100*mdm.ewm(alpha=1/14,adjust=False).mean()/x["atr"].replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    x["adx"]=dx.ewm(alpha=1/14,adjust=False).mean()
    # completed prior-day range only; no current-day lookahead
    d=x.resample("1D",label="left",closed="left").agg({"high":"max","low":"min"}).dropna()
    d["ph"]=d.high.shift(1); d["pl"]=d.low.shift(1)
    day=x.index.floor("D")
    x["d1h"]=day.map(d.ph.to_dict()).to_numpy(); x["d1l"]=day.map(d.pl.to_dict()).to_numpy()
    # Prior completed H4 range, available only after H4 close
    h=x.resample("4h",label="left",closed="left").agg({"high":"max","low":"min"}).dropna()
    h.index=h.index+pd.Timedelta(hours=4)
    h["hh"]=h.high.shift(1).rolling(6,min_periods=6).max()
    h["ll"]=h.low.shift(1).rolling(6,min_periods=6).min()
    x["h4h"]=h.hh.reindex(x.index,method="ffill"); x["h4l"]=h.ll.reindex(x.index,method="ffill")
    # UTC Asian proxy; NOT broker-session truth.
    hours=x.index.hour
    for col,mask,agg in [
        ("asia", (hours<7), None)
    ]:
        pass
    am=x.loc[hours<7].groupby(x.index.floor("D")).agg(ah=("high","max"),al=("low","min"))
    x["ash"]=day.map(am.ah.to_dict()).to_numpy(); x["asl"]=day.map(am.al.to_dict()).to_numpy()
    return x

def configs():
    axes=[
      ("reference",["D1","H4","ASIA"]),
      ("sweep_atr",[0.0,0.03,0.07,0.12]),
      ("reclaim",["close_inside","midrange","opposite_quartile"]),
      ("candle",["direction","body_35"]),
      ("trend",["none","ema50","ema_stack"]),
      ("adx_max",[0,25,35]),
      ("session",["all","london_ny","ny_core"]),
      ("stop_atr",[1.0,1.25,1.5,1.75,2.0]),
      ("rr",[1.0,1.25,1.5,2.0]),
      ("cooldown",[0,3,6,12]),
    ]
    combos=list(itertools.product(*(v for _,v in axes)))
    # Evenly spaced deterministic sample across full Cartesian space; unique 1,000 rows.
    ids=np.linspace(0,len(combos)-1,EXPECTED_COUNT,dtype=int)
    out=[]
    for cid,k in enumerate(ids,1):
        d={axes[i][0]:combos[k][i] for i in range(len(axes))}
        d["candidate_id"]=f"CRT-QE-{cid:04d}"
        out.append(d)
    assert len({tuple(sorted(z.items())) for z in out})==EXPECTED_COUNT
    return out

def measure(trades):
    if not trades: return {"trade_count":0,"net_price_units":0.0,"profit_factor":None,"win_rate_pct":0.0,"avg_r":None,"max_drawdown_r":None}
    a=np.asarray([t["net"] for t in trades],dtype=float); r=np.asarray([t["r"] for t in trades],dtype=float)
    wins=float(a[a>0].sum()); losses=float(-a[a<0].sum())
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
    dd=float(np.max(peak-eq)) if len(eq) else 0.0
    return {"trade_count":len(a),"net_price_units":float(a.sum()),"profit_factor":float(wins/losses) if losses>0 else None,"win_rate_pct":float((a>0).mean()*100),"avg_r":float(r.mean()),"max_drawdown_r":dd}

def run_one(x,cfg,split):
    trades=[]; pos=None; last_exit=-10**9
    for i in range(80,len(x)-1):
        r=x.iloc[i]; t=x.index[i]
        if pos is not None:
            ex=None; reason=""
            if pos["side"]==1 and r.low<=pos["sl"]: ex=pos["sl"]; reason="SL"
            elif pos["side"]==1 and r.high>=pos["tp"]: ex=pos["tp"]; reason="TP"
            elif pos["side"]==-1 and r.high>=pos["sl"]: ex=pos["sl"]; reason="SL"
            elif pos["side"]==-1 and r.low<=pos["tp"]: ex=pos["tp"]; reason="TP"
            if ex is not None:
                gross=(float(ex)-pos["entry"])*pos["side"]
                cost=pos["spread"]+float(r.spread)+0.70
                net=gross-cost
                trades.append({"entry_time":pos["time"],"net":net,"r":net/pos["risk"],"reason":reason})
                pos=None; last_exit=i
        if pos is not None or i-last_exit<cfg["cooldown"]: continue
        if not np.isfinite(r.atr) or r.atr<=0 or not np.isfinite(r.spread) or r.spread<0 or r.spread>0.80: continue
        if cfg["session"]=="london_ny" and not (7<=t.hour<17): continue
        if cfg["session"]=="ny_core" and not (12<=t.hour<20): continue
        if cfg["adx_max"] and ("adx" in x) and np.isfinite(r.adx) and r.adx>cfg["adx_max"]: continue
        if cfg["trend"]=="ema50" and not (r.close>r.ema50 or r.close<r.ema50): continue
        ref=cfg["reference"]
        hi,lo=(r.d1h,r.d1l) if ref=="D1" else ((r.h4h,r.h4l) if ref=="H4" else (r.ash,r.asl))
        if not np.isfinite(hi) or not np.isfinite(lo) or hi<=lo: continue
        p=x.iloc[i-1]; bull=r.close>r.open; bear=r.close<r.open
        body=abs(float(r.close-r.open)); rng=max(float(r.high-r.low),1e-9)
        if cfg["candle"]=="body_35":
            bull=bull and body/rng>=0.35; bear=bear and body/rng>=0.35
        buf=cfg["sweep_atr"]*float(r.atr)
        long=r.low<float(lo)-buf and r.close>lo and bull
        short=r.high>float(hi)+buf and r.close<hi and bear
        if cfg["reclaim"]=="midrange":
            long=long and r.close<(float(hi)+float(lo))/2
            short=short and r.close>(float(hi)+float(lo))/2
        elif cfg["reclaim"]=="opposite_quartile":
            long=long and r.close>float(lo)+0.25*(float(hi)-float(lo))
            short=short and r.close<float(hi)-0.25*(float(hi)-float(lo))
        if cfg["trend"]=="ema50":
            long=long and r.close>r.ema50; short=short and r.close<r.ema50
        elif cfg["trend"]=="ema_stack":
            long=long and r.ema20>r.ema50; short=short and r.ema20<r.ema50
        side=1 if long else (-1 if short else 0)
        if not side: continue
        entry=float(x.open.iloc[i+1]); spr=float(x.spread.iloc[i+1]); dist=cfg["stop_atr"]*float(r.atr)
        pos={"side":side,"entry":entry,"spread":spr,"sl":entry-side*dist,"tp":entry+side*dist*cfg["rr"],"risk":dist,"time":x.index[i+1]}
    if pos:
        r=x.iloc[-1]; gross=(float(r.close)-pos["entry"])*pos["side"]; net=gross-pos["spread"]-float(r.spread)-0.70
        trades.append({"entry_time":pos["time"],"net":net,"r":net/pos["risk"],"reason":"END_OF_DATA_MARK"})
    ins=[z for z in trades if z["entry_time"]<split]; oos=[z for z in trades if z["entry_time"]>=split]
    return {"all":measure(trades),"in_sample":measure(ins),"out_of_sample":measure(oos)},trades

def main():
    if not base.ARCHIVE.exists(): raise FileNotFoundError("Tick archive missing: "+str(base.ARCHIVE))
    actual=base.sha(base.ARCHIVE)
    if base.EXPECTED and actual!=base.EXPECTED: raise RuntimeError("Archive SHA mismatch; aborting")
    ticks,members=base.load(); raw=len(ticks)
    ticks=ticks[(ticks.ask>=ticks.bid)&(ticks.bid>0)&(ticks.ask>0)].drop_duplicates(["timestamp","bid","ask"]).sort_values("timestamp").reset_index(drop=True)
    b=base.bars(ticks)
    if len(b)<100: raise RuntimeError("Insufficient M5 bars")
    x=prepare(b); split=x.index[int(len(x)*.7)]
    cfgs=configs(); rows=[]; ledger=[]
    for c in cfgs:
        met,trades=run_one(x,c,split)
        allm=met["all"]; oos=met["out_of_sample"]; reasons=[]
        if allm["trade_count"]<100: reasons.append("fewer than 100 total trades")
        if oos["trade_count"]<30: reasons.append("fewer than 30 OOS trades")
        if allm["profit_factor"] is None or allm["profit_factor"]<1.20: reasons.append("all-sample PF below 1.20")
        if oos["profit_factor"] is None or oos["profit_factor"]<1.10: reasons.append("OOS PF below 1.10")
        if oos["net_price_units"]<=0: reasons.append("OOS net not positive")
        reasons += ["third-party Dukascopy archive; not PXBT-native verified ticks","M5 OHLC replay, not native MT5 real-tick execution","UTC session proxy not verified against broker server time","commission/swap and account-currency sizing not modelled","walk-forward, cost stress and multiple-testing correction pending"]
        row={**c,"archive_sha256":actual,"raw_tick_rows":raw,"m5_bars":len(x),"split_utc":split.isoformat(),**met,"qualification":{"status":"BLOCKED_RESEARCH_ONLY","passed":False,"reasons":reasons}}
        rows.append(row)
        for z in trades: ledger.append({"candidate_id":c["candidate_id"],"entry_time":z["entry_time"].isoformat(),"net_price_units":z["net"],"r_multiple":z["r"],"exit_reason":z["reason"]})
    df=pd.DataFrame(rows)
    df["oos_pf_sort"]=df["out_of_sample"].map(lambda z:z["profit_factor"] if z["profit_factor"] is not None else -1)
    df["oos_net_sort"]=df["out_of_sample"].map(lambda z:z["net_price_units"])
    df["oos_trades_sort"]=df["out_of_sample"].map(lambda z:z["trade_count"])
    df=df.sort_values(["oos_pf_sort","oos_net_sort","oos_trades_sort"],ascending=False)
    df.drop(columns=["oos_pf_sort","oos_net_sort","oos_trades_sort"]).to_csv(OUT/"daily_crt_quantum_edge_1000.csv",index=False)
    pd.DataFrame(ledger).to_csv(OUT/"daily_crt_quantum_edge_trade_ledger.csv",index=False)
    report={"experiment":"Daily CRT Quantum Edge 1,000-configuration sweep","candidate_count":len(rows),"archive_sha256":actual,"raw_tick_rows":raw,"clean_tick_rows":len(ticks),"m5_bars":len(x),"start_utc":ticks.timestamp.min().isoformat(),"end_utc":ticks.timestamp.max().isoformat(),"split_utc":split.isoformat(),"data_provenance":"Dukascopy third-party; not verified PXBT-native","execution_model":"M5 OHLC replay with next-bar-open entries; stop-first if stop and target occur in same bar","approval":"ALL BLOCKED_RESEARCH_ONLY pending native MT5 real-tick reproduction, longer complete data, broker costs, walk-forward and robustness validation","top_10":df.head(10).drop(columns=["oos_pf_sort","oos_net_sort","oos_trades_sort"]).to_dict(orient="records")}
    (OUT/"daily_crt_quantum_edge_1000.json").write_text(json.dumps(report,indent=2,default=str))
    md=["# Daily CRT Quantum Edge — 1,000 configuration sweep","","**Status: research-only; no candidate approved.**","","- Configurations: 1,000 distinct sampled combinations from the defined Cartesian parameter space.","- Archive SHA-256: "+actual,"- Data: third-party Dukascopy, not verified broker-native ticks.","- Replay: M5 OHLC; not MT5 Every Tick Based on Real Ticks.","- Split: "+split.isoformat(),"","## Top 10 exploratory candidates",""]
    for n,(_,r) in enumerate(df.head(10).iterrows(),1):
        md += [f"{n}. **{r['candidate_id']}** — {r['reference']} / stop {r['stop_atr']} ATR / RR {r['rr']} / trend {r['trend']} / session {r['session']}",f"   - OOS PF: {r['out_of_sample']['profit_factor']}; OOS net: {r['out_of_sample']['net_price_units']:.3f} price units; OOS trades: {r['out_of_sample']['trade_count']}", "   - Status: BLOCKED_RESEARCH_ONLY"]
    md += ["","## Mandatory caveats","", "All rankings are exploratory and subject to multiple-testing/selection bias. The top 10 are not certified winners. Costs are approximated; commissions, swap, contract sizing, broker timezone, native tick sequencing, walk-forward and stress tests remain outstanding."]
    (OUT/"daily_crt_quantum_edge_1000.md").write_text("\n".join(md)+"\n")
    print(json.dumps({"candidate_count":len(rows),"top_5":[{"id":r["candidate_id"],"oos":r["out_of_sample"],"config":{k:r[k] for k in ("reference","sweep_atr","reclaim","trend","stop_atr","rr","session")}} for _,r in df.head(5).iterrows()],"outputs":list(str(p) for p in OUT.glob("daily_crt_quantum_edge*"))},default=str))
if __name__=="__main__": main()
