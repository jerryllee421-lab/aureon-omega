from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

SESSIONS={"ASIA":(0,7),"LONDON":(7,13),"NEW_YORK":(13,21),"LATE":(21,24)}

def label_session(h:int)->str:
    for name,(a,b) in SESSIONS.items():
        if a<=h<b:return name
    return "LATE"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--manifest",required=True)
    a=ap.parse_args()
    df=pd.read_parquet(a.input)
    df["time"]=pd.to_datetime(df["time"],utc=True)
    close=df["mid_close"].astype(float)
    high=df["mid_high"].astype(float); low=df["mid_low"].astype(float)
    ret=close.pct_change()
    tr=pd.concat([(high-low),(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean()
    ema20=close.ewm(span=20,adjust=False).mean(); ema50=close.ewm(span=50,adjust=False).mean()
    df["year"]=df["time"].dt.year
    df["session_utc"]=df["time"].dt.hour.map(label_session)
    df["atr14"]=atr
    df["volatility_96"]=ret.rolling(96,min_periods=48).std()
    df["trend_state"]=((ema20-ema50).abs()/atr.replace(0,pd.NA)).map(lambda x:"TREND" if pd.notna(x) and x>=0.35 else "RANGE")
    spread=df["spread_close"].astype(float)
    df["spread_rolling_median"]=spread.rolling(480,min_periods=50).median()
    df["spread_state"]=(spread/df["spread_rolling_median"].replace(0,pd.NA)).map(lambda x:"WIDE" if pd.notna(x) and x>=1.5 else "NORMAL")
    shock=(ret.abs()/(ret.rolling(480,min_periods=100).std().replace(0,pd.NA)))
    df["shock_state"]=shock.map(lambda x:"SHOCK" if pd.notna(x) and x>=4 else "NORMAL")
    n=len(df); d=int(n*.60); v=int(n*.80)
    df["partition"]="HOLDOUT"
    df.loc[df.index[:d],"partition"]="DEVELOPMENT"
    df.loc[df.index[d:v],"partition"]="VALIDATION"
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    df.to_parquet(out,index=False,compression="zstd")
    manifest={"schema":"aureon.gold_brain.v1","rows":n,"development_rows":d,"validation_rows":v-d,"holdout_rows":n-v,
      "first":df["time"].min().isoformat(),"last":df["time"].max().isoformat(),
      "sessions":df["session_utc"].value_counts().to_dict(),"partitions":df["partition"].value_counts().to_dict()}
    Path(a.manifest).write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
