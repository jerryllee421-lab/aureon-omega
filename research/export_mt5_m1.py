from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="research_data")
    ap.add_argument("--symbol",default="XAUUSD")
    ap.add_argument("--output",required=True)
    ap.add_argument("--point",type=float,default=0.001)
    args=ap.parse_args()

    root=Path(args.root)
    files=sorted((root/args.symbol.upper()/"M1").rglob("*.parquet"))
    if not files:
        raise SystemExit("No M1 parquet files found")

    df=pd.concat((pd.read_parquet(p) for p in files),ignore_index=True)
    df["time"]=pd.to_datetime(df["time"],utc=True)
    df=df.sort_values("time").drop_duplicates("time")
    required=["bid_open","bid_high","bid_low","bid_close","ask_close"]
    missing=[c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    if "bid_volume" in df.columns:
        volume=pd.to_numeric(df["bid_volume"],errors="coerce").fillna(1).clip(lower=1).round().astype("int64")
    else:
        volume=pd.Series(1,index=df.index,dtype="int64")

    if args.spread_multiplier<=0:\n        raise SystemExit("spread-multiplier must be > 0")\n    spread=(((df["ask_close"]-df["bid_close"])/args.point)*args.spread_multiplier).round().clip(lower=1).astype("int64")

    out=pd.DataFrame({
        "time":df["time"].dt.strftime("%Y.%m.%d %H:%M:%S"),
        "open":df["bid_open"],
        "high":df["bid_high"],
        "low":df["bid_low"],
        "close":df["bid_close"],
        "tick_volume":volume,
        "spread":spread,
    })
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(target,index=False,float_format="%.3f")
    print({
        "file":str(target),
        "rows":len(out),
        "first":out["time"].iloc[0],
        "last":out["time"].iloc[-1],
        "spread_points_median":float(spread.median()),
        "volume_source":"bid_volume" if "bid_volume" in df.columns else "fallback_1",
    })


if __name__=="__main__":
    main()
