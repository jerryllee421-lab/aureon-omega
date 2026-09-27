from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

REQUIRED={"time","bid_open","bid_high","bid_low","bid_close","ask_open","ask_high","ask_low","ask_close","mid_open","mid_high","mid_low","mid_close","spread_open","spread_close"}

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args(); p=Path(a.input)
    df=pd.read_parquet(p); missing=sorted(REQUIRED-set(df.columns))
    t=pd.to_datetime(df["time"],utc=True)
    dup=int(t.duplicated().sum()); monotonic=bool(t.is_monotonic_increasing)
    bad_cross=int((df["ask_close"]<df["bid_close"]).sum())
    bad_spread=int((df["spread_close"]<0).sum())
    bad_ohlc=0
    for s in ("bid","ask","mid"):
        o,h,l,c=[df[f"{s}_{k}"] for k in ("open","high","low","close")]
        bad_ohlc+=int((~((h>=o)&(h>=c)&(l<=o)&(l<=c)&(h>=l)&(l>0))).sum())
    gaps=t.sort_values().diff().dropna()
    report={"schema":"aureon.gold_data_gate.v1","file":str(p),"sha256":sha256(p),"rows":len(df),
      "first":t.min().isoformat() if len(t) else None,"last":t.max().isoformat() if len(t) else None,
      "missing_columns":missing,"duplicates":dup,"monotonic_time":monotonic,
      "invalid_ohlc":bad_ohlc,"ask_below_bid":bad_cross,"negative_spread":bad_spread,
      "largest_gap_minutes":float(gaps.max().total_seconds()/60) if len(gaps) else None}
    report["status"]="PASS" if len(df)>0 and not missing and dup==0 and monotonic and bad_ohlc==0 and bad_cross==0 and bad_spread==0 else "FAIL"
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if report["status"]!="PASS":raise SystemExit(4)
if __name__=="__main__":main()
