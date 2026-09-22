from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RULES = {
    "M1":"1min","M2":"2min","M3":"3min","M4":"4min","M5":"5min","M6":"6min",
    "M10":"10min","M12":"12min","M15":"15min","M20":"20min","M30":"30min",
    "H1":"1h","H2":"2h","H3":"3h","H4":"4h","H6":"6h","H8":"8h","H12":"12h",
    "D1":"1D","W1":"1W-MON","MN1":"MS"
}
SIDES = ("bid", "ask", "mid")


def read_m1(root: Path, symbol: str) -> pd.DataFrame:
    files = sorted((root / symbol / "M1").rglob("*.parquet"))
    if not files:
        raise SystemExit("No M1 parquet files found")
    df = pd.concat((pd.read_parquet(p) for p in files), ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").drop_duplicates("time").set_index("time")


def agg_dict():
    d = {}
    for side in SIDES:
        d.update({f"{side}_open":"first",f"{side}_high":"max",f"{side}_low":"min",f"{side}_close":"last"})
    d.update({"bid_volume":"sum","ask_volume":"sum","spread_open":"mean","spread_close":"mean"})
    return d


def validate(df: pd.DataFrame) -> dict:
    x = df.reset_index()
    dup = int(x["time"].duplicated().sum())
    invalid = 0
    for side in SIDES:
        o,h,l,c = [x[f"{side}_{k}"] for k in ("open","high","low","close")]
        invalid += int((~((h >= o) & (h >= c) & (l <= o) & (l <= c) & (h >= l) & (l > 0))).sum())
    nulls = int(x.isna().sum().sum())
    return {
        "rows": int(len(x)), "duplicates": dup, "invalid_ohlc": invalid, "null_cells": nulls,
        "first": x["time"].min().isoformat() if len(x) else None,
        "last": x["time"].max().isoformat() if len(x) else None,
        "status": "PASS" if len(x) and dup == 0 and invalid == 0 and nulls == 0 else "FAIL"
    }


def file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="research_data")
    ap.add_argument("--symbol",default="XAUUSD")
    args=ap.parse_args()
    root=Path(args.root); symbol=args.symbol.upper()
    m1=read_m1(root,symbol)
    reports={}
    outroot=root/symbol/"canonical"; outroot.mkdir(parents=True,exist_ok=True)
    for tf,rule in RULES.items():
        if tf=="M1": df=m1.copy()
        else:
            df=m1.resample(rule,label="left",closed="left").agg(agg_dict()).dropna(subset=["bid_open","ask_open"])
        out=outroot/f"{symbol}_{tf}.parquet"
        df.reset_index().to_parquet(out,index=False,compression="zstd")
        rep=validate(df)
        rep["sha256"]=file_hash(out); rep["file"]=str(out)
        reports[tf]=rep
        print(tf,rep)
    overall = "PASS" if all(v["status"]=="PASS" for v in reports.values()) else "FAIL"
    manifest={"symbol":symbol,"source":"DUKASCOPY_EXTERNAL","generated_at":datetime.now(timezone.utc).isoformat(),"overall":overall,"timeframes":reports}
    (root/symbol/"validation_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    if overall!="PASS": raise SystemExit(3)

if __name__=="__main__": main()
