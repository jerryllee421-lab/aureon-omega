from __future__ import annotations
import argparse,json,os,datetime
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument("--state",required=True);p.add_argument("--stage",required=True);p.add_argument("--task",required=True);p.add_argument("--completed",type=int);p.add_argument("--total",type=int);p.add_argument("--unit",default="steps");p.add_argument("--blocker");p.add_argument("--out",default="research_results/project_status.json");a=p.parse_args()
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 progress=None
 if a.completed is not None and a.total is not None and a.total>0 and 0<=a.completed<=a.total: progress={"completed":a.completed,"total":a.total,"unit":a.unit}
 d={"schema":"aureon.project.status.v1","state":a.state,"stage":a.stage,"currentTask":a.task,"progress":progress,"blocker":a.blocker,"commitSha":os.getenv("CIRCLE_SHA1") or os.getenv("GITHUB_SHA"),"observedAt":now}
 q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(d,indent=2));print(json.dumps(d))
if __name__=="__main__":main()
