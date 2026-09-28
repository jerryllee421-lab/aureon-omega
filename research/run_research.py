from __future__ import annotations
import argparse, itertools, json, math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from fvg_v211 import Params, run, trades_frame, prepare


def load(path:Path):
    df=pd.read_parquet(path); df["time"]=pd.to_datetime(df["time"],utc=True); return df.sort_values("time").reset_index(drop=True)

def split(df, s):
    n=len(df); a=int(n*s["development"]); b=int(n*(s["development"]+s["validation"]))
    return df.iloc[:a].copy(),df.iloc[a:b].copy(),df.iloc[b:].copy()

def score(m, min_trades):
    if m["trades"]<min_trades: return -1e9
    pf=min(m["profit_factor"],5); return m["expectancy_r"]*4 + math.log1p(max(pf,0)) - .06*m["max_drawdown_r"] + .001*min(m["trades"],1000)

def monte_carlo(rs, paths, seed, initial_equity, risk_pct, ruin_dd_pct):
    if len(rs)==0:return {"paths":0}
    rng=np.random.default_rng(seed); maxdds=[]; finals=[]
    for _ in range(paths):
        sample=rng.choice(rs,size=len(rs),replace=True); eq=initial_equity; peak=eq; mdd=0
        for r in sample:
            eq*=max(0.000001,1+(risk_pct/100.0)*r); peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak*100)
        maxdds.append(mdd); finals.append(eq)
    a=np.array(maxdds); f=np.array(finals)
    return {"paths":paths,"median_final_equity":float(np.median(f)),"p05_final_equity":float(np.quantile(f,.05)),"median_max_dd_pct":float(np.median(a)),"p95_max_dd_pct":float(np.quantile(a,.95)),"ruin_probability":float((a>=ruin_dd_pct).mean())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="research/config/fvg_v211_baseline.yml"); ap.add_argument("--data",required=True); ap.add_argument("--out",default="research_results"); ap.add_argument("--max-candidates",type=int,default=120)
    args=ap.parse_args(); cfg=yaml.safe_load(Path(args.config).read_text()); df=load(Path(args.data)); dev,val,hold=split(df,cfg["splits"]); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    base=Params(**{k:v for k,v in cfg["baseline"].items() if k in Params.__dataclass_fields__})
    base_tr,base_m=run(df,base); trades_frame(base_tr).to_csv(out/"baseline_trades.csv",index=False)
    grid=cfg["grid"]; keys=list(grid); all_combos=list(itertools.product(*(grid[k] for k in keys)))\n    if args.max_candidates < len(all_combos):\n        pick=np.linspace(0,len(all_combos)-1,num=args.max_candidates,dtype=int)\n        combos=[all_combos[i] for i in dict.fromkeys(pick.tolist())]\n    else:\n        combos=all_combos
    rows=[]
    for idx,vals in enumerate(combos):
        kw=asdict(base); kw.update(dict(zip(keys,vals))); p=Params(**kw); tr,m=run(dev,p); m["score"]=score(m,cfg["research_guardrails"]["min_trades_dev"]); rows.append({"candidate":idx,"params":kw,"dev":m})
    rows.sort(key=lambda z:z["dev"]["score"],reverse=True); finalists=rows[:min(12,len(rows))]
    for item in finalists:
        p=Params(**item["params"]); _,item["validation"]=run(val,p); ht, item["holdout"]=run(hold,p); item["monte_carlo"]=monte_carlo(np.array([t.r for t in ht]),cfg["research_guardrails"]["monte_carlo_paths"],cfg["research_guardrails"]["random_seed"],cfg["research_guardrails"]["initial_equity"],cfg["research_guardrails"]["research_risk_percent"],cfg["research_guardrails"]["monte_carlo_max_ruin_drawdown_pct"])
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"strategy":cfg["strategy"],"source":cfg["data_source"],"execution_model":cfg["execution_model"],"rows":len(df),"period":{"first":df.time.iloc[0].isoformat(),"last":df.time.iloc[-1].isoformat()},"baseline":base_m,"candidates_tested":len(rows),"finalists":finalists,"warning":"Python results are research approximations, not MT5 tick-equivalent results. Final candidates require MT5 real-tick verification."}
    (out/"research_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame([{**{"candidate":r["candidate"]},**{f"p_{k}":v for k,v in r["params"].items()},**{f"dev_{k}":v for k,v in r["dev"].items()}} for r in rows]).to_csv(out/"candidate_dev_results.csv",index=False)
    print(json.dumps({k:report[k] for k in ("strategy","rows","period","baseline","candidates_tested")},indent=2))
if __name__=="__main__":main()
