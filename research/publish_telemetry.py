from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

def _env():
 u=os.getenv("SUPABASE_URL","").rstrip("/")
 k=os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
 if not u or not k:return None
 return u,k

def publish_status_file(path="research_results/project_status.json"):
 e=_env()
 if not e:return False
 p=Path(path)
 if not p.exists():return False
 d=json.loads(p.read_text())
 row={"observed_at":d.get("observedAt"),"state":d.get("state","UNKNOWN"),"stage":d.get("stage"),
      "current_task":d.get("currentTask"),"completed":(d.get("progress") or {}).get("completed"),
      "total":(d.get("progress") or {}).get("total"),"unit":(d.get("progress") or {}).get("unit"),
      "blocker":d.get("blocker"),"commit_sha":d.get("commitSha"),"payload":d}
 return _post("project_status_events",row,*e)

def publish_research_report(path="research_results/research_report.json"):
 e=_env()
 if not e:return False
 p=Path(path)
 if not p.exists():return False
 d=json.loads(p.read_text()); best=d.get("best") or d.get("best_candidate") or {}
 if not best:return False
 run=d.get("run_id") or d.get("dataset_sha256") or os.getenv("CIRCLE_WORKFLOW_ID") or os.getenv("CIRCLE_SHA1") or "unknown"
 row={"run_id":str(run),"candidate":str(best.get("name") or best.get("candidate") or "unknown"),
      "verdict":str(best.get("verdict") or d.get("verdict") or "RESEARCH"),
      "net":best.get("net") or best.get("net_profit"),"profit_factor":best.get("profit_factor"),
      "drawdown_pct":best.get("drawdown_pct"),"trades":best.get("trades"),"expectancy_r":best.get("expectancy_r"),
      "oos_status":best.get("oos_status"),"holdout_status":best.get("holdout_status"),
      "dataset_sha256":d.get("dataset_sha256"),"source_commit":os.getenv("CIRCLE_SHA1") or os.getenv("GITHUB_SHA"),
      "artifact":path,"metrics":best}
 return _post("research_test_results",row,*e,prefer="resolution=merge-duplicates")

def _post(table,row,url,key,prefer="return=minimal"):
 req=urllib.request.Request(url+"/rest/v1/"+table,data=json.dumps(row).encode(),method="POST",
  headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Prefer":prefer})
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return 200<=r.status<300
 except Exception as ex:
  print("TELEMETRY_PUBLISH_FAILED",table,type(ex).__name__);return False

if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser();a.add_argument("kind",choices=["status","result"]);a.add_argument("--path");x=a.parse_args()
 ok=publish_status_file(x.path or "research_results/project_status.json") if x.kind=="status" else publish_research_report(x.path or "research_results/research_report.json")
 raise SystemExit(0 if ok else 2)
