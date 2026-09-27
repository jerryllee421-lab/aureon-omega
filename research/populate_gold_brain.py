from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import date
from pathlib import Path

def run(cmd):
    print("+"," ".join(map(str,cmd)),flush=True)
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",required=True)
    ap.add_argument("--end",default=date.today().isoformat())
    ap.add_argument("--root",default="research_data")
    ap.add_argument("--workers",type=int,default=12)
    ap.add_argument("--brain-tf",default="M1")
    a=ap.parse_args()
    root=Path(a.root); xau=root/"XAUUSD"
    run([sys.executable,"research/duka_m1.py","--symbol","XAUUSD","--start",a.start,"--end",a.end,"--workers",str(a.workers),"--output",a.root])
    run([sys.executable,"research/resample_validate.py","--root",a.root,"--symbol","XAUUSD"])
    canonical=xau/"canonical"/f"XAUUSD_{a.brain_tf}.parquet"
    gate=xau/"gold_data_gate.json"
    run([sys.executable,"research/gold_data_gate.py","--input",str(canonical),"--out",str(gate)])
    brain=xau/"brain"/f"XAUUSD_{a.brain_tf}_brain.parquet"
    manifest=xau/"brain"/"gold_brain_manifest.json"
    run([sys.executable,"research/gold_brain.py","--input",str(canonical),"--output",str(brain),"--manifest",str(manifest)])
    summary={"schema":"aureon.gold_population.v1","status":"PASS","start":a.start,"end":a.end,
      "canonical":str(canonical),"brain":str(brain),"data_gate":str(gate),"brain_manifest":str(manifest)}
    (xau/"population_manifest.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
