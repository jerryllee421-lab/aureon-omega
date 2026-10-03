#!/usr/bin/env python3
"""Normalize AUREON V9.3 MT5 evidence into a governed research report.

Research-only: no broker orders. Candidate selection uses VALIDATION only;
HOLDOUT is read only after a candidate has been selected.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,re
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

SUMMARY_NAME="AUREON_V9_3_FORENSICS_SUMMARY.csv"
PERIOD_NAME="AUREON_V9_3_PERIOD_SUMMARY.csv"
SIGNALS_NAME="AUREON_V9_3_FORENSICS_SIGNALS.csv"
TRADES_NAME="AUREON_V9_3_FORENSICS_TRADES.csv"
EVENTS_NAME="AUREON_V9_3_FORENSICS_EVENTS.csv"
HALFYEAR_RE=re.compile(r"^\d{4}-H[12]$")

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def read_csv(path:Path)->list[dict[str,str]]:
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f,delimiter=";"))
    if not rows: raise ValueError("empty CSV: {}".format(path))
    return rows

def num(row,key,default=0.0):
    raw=row.get(key)
    if raw in (None,""): return float(default)
    value=float(raw)
    if not math.isfinite(value): raise ValueError("non-finite {}={}".format(key,raw))
    return value

def integer(row,key,default=0):
    raw=row.get(key)
    return int(float(raw)) if raw not in (None,"") else int(default)

def vid(row): return integer(row,"variant_id",-1)

def unique(rows,key_fn):
    out={}
    for row in rows:
        key=key_fn(row)
        if key in out: raise ValueError("duplicate evidence key: {}".format(key))
        out[key]=row
    return out

def metrics(row):
    return {
      "trades":integer(row,"portfolio_trades",integer(row,"trades",0)),
      "profit_factor":num(row,"profit_factor"),
      "expectancy_r":num(row,"portfolio_expectancy_R"),
      "net_r":num(row,"net_R"),
      "max_drawdown_r":num(row,"max_dd_R"),
      "event_fast_n":integer(row,"event_fast_n"),
      "event_fast_expectancy_r":num(row,"event_fast_expectancy_R"),
      "event_slow_n":integer(row,"event_slow_n"),
      "event_slow_expectancy_r":num(row,"event_slow_expectancy_R"),
    }

def validation_score(row):
    m=metrics(row); n=m["trades"]; pf=m["profit_factor"]; exp=m["expectancy_r"]
    if n<=0: return -1e9
    return exp*max(0.0,min(pf,4.0))*math.sqrt(n)

def degradation(validation_exp,holdout_exp):
    if validation_exp<=0: return 999.0 if holdout_exp<=0 else 0.0
    return max(0.0,100.0*(validation_exp-holdout_exp)/abs(validation_exp))

def build_report(root:Path,dataset_sha256=None,source_commit=None):
    summary=read_csv(root/SUMMARY_NAME)
    periods=read_csv(root/PERIOD_NAME)
    overall=unique(summary,vid)
    if 0 not in overall or str(overall[0].get("variant"))!="CONTROL":
        raise ValueError("CONTROL variant 0 is missing or renamed")
    pidx=unique(periods,lambda r:(str(r.get("period_or_fold")),vid(r)))
    validation={v:r for (label,v),r in pidx.items() if label=="FOLD_VALIDATION" and v!=0}
    if not validation: raise ValueError("no challenger FOLD_VALIDATION rows found")
    ranked=sorted(validation.items(),key=lambda kv:validation_score(kv[1]),reverse=True)
    selected_id,valrow=ranked[0]
    selected=overall.get(selected_id)
    if selected is None: raise ValueError("selected variant has no overall summary")
    holdrow=pidx.get(("FOLD_HOLDOUT",selected_id))
    if holdrow is None: raise ValueError("selected variant has no FOLD_HOLDOUT evidence")
    devrow=pidx.get(("FOLD_DEV",selected_id))
    name=str(selected.get("variant") or "VARIANT_{}".format(selected_id))
    val=metrics(valrow); hold=metrics(holdrow); base=metrics(selected); control=metrics(overall[0])
    dev=metrics(devrow) if devrow else None
    halfyears=sorted((label,metrics(r)) for (label,v),r in pidx.items() if v==selected_id and HALFYEAR_RE.match(label))
    positive=sum(1 for _,m in halfyears if m["expectancy_r"]>0)
    ratio=positive/len(halfyears) if halfyears else None
    valid_ok=val["trades"]>=20 and val["profit_factor"]>=1.0 and val["expectancy_r"]>0
    hold_ok=hold["trades"]>0 and hold["profit_factor"]>=1.0 and hold["expectancy_r"]>0
    manifest={}
    for fn in (SUMMARY_NAME,PERIOD_NAME,SIGNALS_NAME,TRADES_NAME,EVENTS_NAME):
        p=root/fn
        if p.exists(): manifest[fn]={"sha256":sha256(p),"bytes":p.stat().st_size}
    leaderboard=[{"variant_id":v,"variant":r.get("variant"),"validation_score":validation_score(r),"validation":metrics(r)} for v,r in ranked]
    verdict="RESEARCH_CANDIDATE" if valid_ok and hold_ok else "REJECT_OR_REPAIR"
    report={
      "schema":"aureon.research_evidence.v2",
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "run_id":os.getenv("CIRCLE_WORKFLOW_ID") or os.getenv("GITHUB_RUN_ID") or manifest[SUMMARY_NAME]["sha256"][:24],
      "strategy":"AUREON_V9_3_MARKET_RELATIONSHIP_FORENSICS","strategy_version":"9.3",
      "selection_rule":"rank challengers on FOLD_VALIDATION only; inspect FOLD_HOLDOUT only after selection",
      "dataset_sha256":dataset_sha256,
      "source_commit":source_commit or os.getenv("CIRCLE_SHA1") or os.getenv("GITHUB_SHA"),
      "control":{"name":"CONTROL",**control},"selected_candidate":name,"candidate_id":selected_id,
      "baseline":base,"development":dev,"validation":val,"holdout":hold,
      "oos_degradation_pct":degradation(val["expectancy_r"],hold["expectancy_r"]),
      "positive_halfyear_ratio":ratio,"positive_halfyears":positive,"halfyears_observed":len(halfyears),
      "oos_status":"PASS" if valid_ok else "FAIL","holdout_status":"PASS" if hold_ok else "FAIL",
      "verdict":verdict,"validation_leaderboard":leaderboard,
      "halfyear_metrics":[{"period":p,**m} for p,m in halfyears],
      "input_manifest":manifest,
      "warning":"Research evidence only. This report grants no LIVE or DEMO execution authority."
    }
    report["best"]={
      "name":name,"candidate":selected_id,"verdict":verdict,"net":base["net_r"],
      "profit_factor":base["profit_factor"],"trades":base["trades"],"expectancy_r":base["expectancy_r"],
      "oos_status":report["oos_status"],"holdout_status":report["holdout_status"],
      "validation":val,"holdout":hold,"positive_halfyear_ratio":ratio,
      "oos_degradation_pct":report["oos_degradation_pct"]
    }
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",required=True,type=Path)
    ap.add_argument("--out",default="research_results/research_report.json",type=Path)
    ap.add_argument("--dataset-sha256"); ap.add_argument("--source-commit")
    a=ap.parse_args()
    report=build_report(a.input_dir,a.dataset_sha256,a.source_commit)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps({"selected_candidate":report["selected_candidate"],"oos_status":report["oos_status"],
      "holdout_status":report["holdout_status"],"positive_halfyear_ratio":report["positive_halfyear_ratio"],"out":str(a.out)},indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
