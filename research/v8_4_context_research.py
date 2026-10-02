from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def wilder(s, n):
    return s.ewm(alpha=1.0/n, adjust=False, min_periods=n).mean()


def enrich(x):
    x=x.copy()
    h,l,c=x.bid_high,x.bid_low,x.bid_close
    prev=c.shift(1)
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    x["atr"]=wilder(tr,14)
    d=c.diff(); up=d.clip(lower=0); dn=(-d).clip(lower=0)
    rs=wilder(up,14)/wilder(dn,14).replace(0,np.nan)
    x["rsi"]=100-100/(1+rs)
    upm=h.diff(); dnm=-l.diff()
    pdm=pd.Series(np.where((upm>dnm)&(upm>0),upm,0.0),index=x.index)
    mdm=pd.Series(np.where((dnm>upm)&(dnm>0),dnm,0.0),index=x.index)
    aw=wilder(tr,14)
    pdi=100*wilder(pdm,14)/aw.replace(0,np.nan)
    mdi=100*wilder(mdm,14)/aw.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    x["adx"]=wilder(dx,14)
    x["ema9"]=c.ewm(span=9,adjust=False,min_periods=9).mean()
    x["ema21"]=c.ewm(span=21,adjust=False,min_periods=21).mean()
    return x


def load_m1(root):
    files=sorted((Path(root)/"XAUUSD"/"M1").rglob("*.parquet"))
    if not files:
        raise SystemExit("No M1 parquet files")
    x=pd.concat((pd.read_parquet(p) for p in files),ignore_index=True)
    x["time"]=pd.to_datetime(x.time,utc=True)
    return x.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def build_m5(m1):
    x=m1.set_index("time")
    agg={}
    for side in ("bid","ask"):
        agg.update({f"{side}_open":"first",f"{side}_high":"max",f"{side}_low":"min",f"{side}_close":"last"})
    return enrich(x.resample("5min",label="left",closed="left").agg(agg).dropna().reset_index())


def anchors(m5):
    x=m5.copy()
    x["p20lo"]=x.bid_low.shift(1).rolling(20).min()
    x["p20hi"]=x.bid_high.shift(1).rolling(20).max()
    x["atrmed"]=x.atr.rolling(50).median()
    vr=x.atr/x.atrmed.replace(0,np.nan)
    le=(x.ema21-x.bid_close)/x.atr
    se=(x.bid_close-x.ema21)/x.atr
    session=x.time.dt.hour.between(7,11)
    vol=(vr>=0.8)&(vr<1.8)
    lm=session&vol&(x.bid_low<x.p20lo)&(x.bid_close>x.p20lo)&(x.rsi<=30)&(x.adx<=30)&(le>=2.0)
    sm=session&vol&(x.bid_high>x.p20hi)&(x.bid_close<x.p20hi)&(x.rsi>=70)&(x.adx<=30)&(se>=2.0)
    rows=[]
    for i in np.flatnonzero(lm.to_numpy()):
        rows.append((x.time.iloc[i]+pd.Timedelta(minutes=5),1))
    for i in np.flatnonzero(sm.to_numpy()):
        rows.append((x.time.iloc[i]+pd.Timedelta(minutes=5),-1))
    a=pd.DataFrame(rows,columns=["active_from","direction"]).sort_values("active_from").reset_index(drop=True)
    a["anchor_id"]=np.arange(len(a))
    return a


def map_context(m1,a):
    x=enrich(m1)
    x["p5hi"]=x.bid_high.shift(2).rolling(5).max()
    x["p5lo"]=x.bid_low.shift(2).rolling(5).min()
    x["p8hi"]=x.bid_high.shift(2).rolling(8).max()
    x["p8lo"]=x.bid_low.shift(2).rolling(8).min()
    mt=x.time.astype("int64").to_numpy()
    at=a.active_from.astype("int64").to_numpy()
    pos=np.searchsorted(at,mt,side="right")-1
    good=pos>=0
    p=np.where(good,pos,0)
    age=(mt-at[p])/60_000_000_000
    good &= (age>=0)&(age<=60)
    x["anchor_id"]=np.where(good,a.anchor_id.to_numpy()[p],-1)
    x["direction"]=np.where(good,a.direction.to_numpy()[p],0)
    x["age_min"]=np.where(good,age,np.nan)
    return x


def trigger_rows(x):
    rows=[]
    for i in range(60,len(x)-21):
        d=int(x.direction.iloc[i])
        if d==0 or not np.isfinite(x.atr.iloc[i]) or x.atr.iloc[i]<=0:
            continue
        c,o,h,l=x.bid_close.iloc[i],x.bid_open.iloc[i],x.bid_high.iloc[i],x.bid_low.iloc[i]
        atr=x.atr.iloc[i]
        tests={}
        if d>0:
            tests["SWEEP"]=l<x.p8lo.iloc[i] and c>x.p8lo.iloc[i]
            tests["EMA_RECLAIM"]=c>x.ema9.iloc[i] and x.bid_close.iloc[i-1]<=x.ema9.iloc[i-1] and x.ema9.iloc[i]>=x.ema21.iloc[i]
            tests["MOM"]=c>o and (c-o)>=0.60*atr and x.rsi.iloc[i]>=52
            tests["BREAK"]=c>x.p5hi.iloc[i]
        else:
            tests["SWEEP"]=h>x.p8hi.iloc[i] and c<x.p8hi.iloc[i]
            tests["EMA_RECLAIM"]=c<x.ema9.iloc[i] and x.bid_close.iloc[i-1]>=x.ema9.iloc[i-1] and x.ema9.iloc[i]<=x.ema21.iloc[i]
            tests["MOM"]=c<o and (o-c)>=0.60*atr and x.rsi.iloc[i]<=48
            tests["BREAK"]=c<x.p5lo.iloc[i]
        j=i+1
        entry=x.ask_open.iloc[j] if d>0 else x.bid_open.iloc[j]
        for name,flag in tests.items():
            if flag:
                rows.append({
                    "time":x.time.iloc[j],"anchor_id":int(x.anchor_id.iloc[i]),"direction":d,
                    "age_min":float(x.age_min.iloc[i]),"trigger":name,"entry_idx":j,
                    "entry":float(entry),"atr":float(atr)
                })
    return pd.DataFrame(rows)


def add_forward_outcomes(c,x,horizons=(5,10,15,20)):
    bh=x.bid_high.to_numpy(); bl=x.bid_low.to_numpy(); bc=x.bid_close.to_numpy()
    ah=x.ask_high.to_numpy(); al=x.ask_low.to_numpy(); ac=x.ask_close.to_numpy()
    for hz in horizons:
        ret=[]; mfe=[]; mae=[]
        for row in c.itertuples(index=False):
            j=int(row.entry_idx); end=min(len(x)-1,j+hz-1); d=int(row.direction); e=float(row.entry); a=float(row.atr)
            if d>0:
                ret.append((bc[end]-e)/a)
                mfe.append((np.max(bh[j:end+1])-e)/a)
                mae.append((e-np.min(bl[j:end+1]))/a)
            else:
                ret.append((e-ac[end])/a)
                mfe.append((e-np.min(al[j:end+1]))/a)
                mae.append((np.max(ah[j:end+1])-e)/a)
        c[f"ret_{hz}"]=ret; c[f"mfe_{hz}"]=mfe; c[f"mae_{hz}"]=mae
    return c


def summarize(c):
    if c.empty:
        return pd.DataFrame()
    t0=c.time.min(); t1=c.time.max(); span=t1-t0
    c=c.copy()
    c["split"]=np.where(c.time<t0+span*0.60,"train",np.where(c.time<t0+span*0.80,"validation","test"))
    c["age_bucket"]=pd.cut(c.age_min,[-0.1,10,20,30,45,60],labels=["0-10","10-20","20-30","30-45","45-60"])
    rows=[]
    for keys,z in c.groupby(["trigger","direction","age_bucket","split"],observed=True):
        trig,d,age,split=keys
        row={"trigger":trig,"direction":int(d),"age_bucket":str(age),"split":split,"n":len(z)}
        for hz in (5,10,15,20):
            row[f"mean_ret_{hz}"]=float(z[f"ret_{hz}"].mean())
            row[f"median_ret_{hz}"]=float(z[f"ret_{hz}"].median())
            row[f"mfe_gt1_mae_lt1_{hz}"]=float(((z[f"mfe_{hz}"]>=1.0)&(z[f"mae_{hz}"]<1.0)).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="research_data")
    ap.add_argument("--out",default="v8_4_context_results")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    m1=load_m1(args.root)
    m5=build_m5(m1)
    a=anchors(m5)
    x=map_context(m1,a)
    c=trigger_rows(x)
    c=add_forward_outcomes(c,x)
    s=summarize(c)

    a.to_csv(out/"anchors.csv",index=False)
    c.to_csv(out/"micro_context_events.csv",index=False)
    s.to_csv(out/"context_summary.csv",index=False)

    stable=[]
    if len(s):
        for (trig,d,age),z in s.groupby(["trigger","direction","age_bucket"],observed=True):
            if set(z.split)=={"train","validation","test"}:
                q=z.set_index("split")
                for hz in (5,10,15,20):
                    vals=[q.loc[k,f"mean_ret_{hz}"] for k in ("train","validation","test")]
                    ns=[q.loc[k,"n"] for k in ("train","validation","test")]
                    if min(ns)>=20 and min(vals)>0:
                        stable.append({
                            "trigger":trig,"direction":int(d),"age_bucket":str(age),"horizon_min":hz,
                            "train_n":int(ns[0]),"val_n":int(ns[1]),"test_n":int(ns[2]),
                            "train_mean_r":float(vals[0]),"val_mean_r":float(vals[1]),"test_mean_r":float(vals[2]),
                            "robust_mean_r":float(min(vals))
                        })
    sd=pd.DataFrame(stable)
    if len(sd):
        sd=sd.sort_values(["robust_mean_r","test_n"],ascending=False)
    sd.to_csv(out/"stable_contexts.csv",index=False)

    report={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "strategy":"AUREON V8.4 CONTEXT RESEARCH",
        "m1_rows":int(len(m1)),
        "m5_anchors":int(len(a)),
        "micro_events":int(len(c)),
        "stable_contexts":int(len(sd)),
        "best_context":sd.iloc[0].to_dict() if len(sd) else None,
        "method":"Frozen V7-style M5 context + M1 trigger forward-excursion analysis, chronological 60/20/20.",
        "warning":"Research diagnostics only; no order execution and no MT5 real-tick parity claim."
    }
    (out/"report.json").write_text(json.dumps(report,indent=2,default=float),encoding="utf-8")
    print(json.dumps(report,indent=2,default=float))


if __name__=="__main__":
    main()
