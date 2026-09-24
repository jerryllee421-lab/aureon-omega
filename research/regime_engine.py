from __future__ import annotations

"""Deterministic ASTRA market-regime labelling for XAUUSD research data.

The classifier is intentionally transparent: trend is derived from EMA
separation/slope, volatility from ATR percentile, and compression/expansion
from rolling range/ATR behavior. It does not forecast. It labels only using
information available at or before each completed bar.
"""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def load_m1(root: Path) -> pd.DataFrame:
    files=sorted((root/"XAUUSD"/"M1").rglob("*.parquet"))
    if not files:
        raise SystemExit("No XAUUSD M1 parquet files found")
    x=pd.concat((pd.read_parquet(p) for p in files),ignore_index=True)
    x["time"]=pd.to_datetime(x["time"],utc=True)
    return x.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def resample(x: pd.DataFrame, rule: str) -> pd.DataFrame:
    q=x.set_index("time")
    out=pd.DataFrame({
        "open":q["bid_open"].resample(rule,label="right",closed="right").first(),
        "high":q["bid_high"].resample(rule,label="right",closed="right").max(),
        "low":q["bid_low"].resample(rule,label="right",closed="right").min(),
        "close":q["bid_close"].resample(rule,label="right",closed="right").last(),
    }).dropna().reset_index()
    return out


def add_features(x: pd.DataFrame, fast: int=20, slow: int=50, atr_n: int=14) -> pd.DataFrame:
    y=x.copy()
    prev=y["close"].shift(1)
    tr=pd.concat([
        (y["high"]-y["low"]).abs(),
        (y["high"]-prev).abs(),
        (y["low"]-prev).abs(),
    ],axis=1).max(axis=1)
    y["atr"]=tr.ewm(alpha=1/atr_n,adjust=False,min_periods=atr_n).mean()
    y["ema_fast"]=y["close"].ewm(span=fast,adjust=False,min_periods=fast).mean()
    y["ema_slow"]=y["close"].ewm(span=slow,adjust=False,min_periods=slow).mean()
    y["ema_gap_atr"]=(y["ema_fast"]-y["ema_slow"])/y["atr"].replace(0,np.nan)
    y["slow_slope_atr"]=(y["ema_slow"]-y["ema_slow"].shift(3))/(3*y["atr"].replace(0,np.nan))
    y["atr_pct"]=y["atr"].rolling(252,min_periods=80).rank(pct=True)
    y["range20_atr"]=(y["high"].rolling(20).max()-y["low"].rolling(20).min())/y["atr"].replace(0,np.nan)
    y["efficiency20"]=(y["close"]-y["close"].shift(20)).abs() / (
        y["close"].diff().abs().rolling(20).sum().replace(0,np.nan)
    )
    return y


def classify_row(r) -> str:
    if not np.isfinite(r.atr_pct) or not np.isfinite(r.ema_gap_atr):
        return "WARMUP"
    gap=float(r.ema_gap_atr)
    slope=float(r.slow_slope_atr) if np.isfinite(r.slow_slope_atr) else 0.0
    atrp=float(r.atr_pct)
    eff=float(r.efficiency20) if np.isfinite(r.efficiency20) else 0.0
    rng=float(r.range20_atr) if np.isfinite(r.range20_atr) else 0.0

    if atrp <= 0.20 and rng <= 7.0:
        return "COMPRESSION"
    if atrp >= 0.85:
        if gap >= 0.25 and slope > 0:
            return "EXPANSION_UP"
        if gap <= -0.25 and slope < 0:
            return "EXPANSION_DOWN"
        return "HIGH_VOL_TRANSITION"
    if gap >= 0.35 and slope > 0.015 and eff >= 0.22:
        return "TREND_UP"
    if gap <= -0.35 and slope < -0.015 and eff >= 0.22:
        return "TREND_DOWN"
    if abs(gap) <= 0.25 and eff <= 0.28:
        return "RANGE"
    return "TRANSITION"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="research_data")
    ap.add_argument("--tf",default="15min")
    ap.add_argument("--fast",type=int,default=20)
    ap.add_argument("--slow",type=int,default=50)
    ap.add_argument("--out",default="regime_results")
    args=ap.parse_args()
    if args.fast>=args.slow:
        raise SystemExit("fast EMA must be < slow EMA")

    x=add_features(resample(load_m1(Path(args.root)),args.tf),args.fast,args.slow)
    x["regime"]=x.apply(classify_row,axis=1)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    x.to_parquet(out/"regimes.parquet",index=False)
    counts=x["regime"].value_counts().to_dict()
    payload={
        "timeframe":args.tf,
        "fast_ema":args.fast,
        "slow_ema":args.slow,
        "first":str(x["time"].min()),
        "last":str(x["time"].max()),
        "bars":int(len(x)),
        "regime_counts":{k:int(v) for k,v in counts.items()},
        "method":"closed-bar deterministic EMA/ATR/range/efficiency classifier",
    }
    (out/"summary.json").write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))


if __name__=="__main__":
    main()
