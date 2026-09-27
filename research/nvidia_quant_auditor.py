from __future__ import annotations
import json, os, sys, urllib.request
from pathlib import Path

MODEL=os.getenv("NVIDIA_MODEL","nvidia/nemotron-3.5-lightning-30b-a3b")
KEY=os.getenv("NVIDIA_API_KEY","").strip()
report=Path(sys.argv[1] if len(sys.argv)>1 else "research_results/research_report.json")
out=Path(sys.argv[2] if len(sys.argv)>2 else "research_results/astra_nvidia_review.json")
if not report.exists():
    raise SystemExit(f"missing report: {report}")
data=json.loads(report.read_text(encoding="utf-8"))
if not KEY:
    out.write_text(json.dumps({"status":"SKIPPED_NO_NVIDIA_API_KEY","model":MODEL},indent=2))
    print("NVIDIA advisory skipped: NVIDIA_API_KEY is not configured.")
    raise SystemExit(0)

payload={
 "model":MODEL,"temperature":0.2,"top_p":0.95,"max_tokens":3000,"stream":False,
 "messages":[
  {"role":"system","content":"You are ASTRA Quant Auditor. You may analyze supplied deterministic research results, but you must never invent metrics, alter test results, authorize real-money trading, or treat your opinion as evidence. Return concise JSON only with keys verdict, evidence, risks, next_experiments. verdict must be PROMOTE_TO_NEXT_RESEARCH_GATE, HOLD, or REJECT. Prefer robustness, holdout stability, adequate sample size, and drawdown control over headline profit."},
  {"role":"user","content":"Audit this XAUUSD research report. The deterministic engine is authoritative. Identify overfitting/regime/dependency risks and propose at most 5 controlled next experiments changing as few variables as possible. Report:\n"+json.dumps(data,separators=(",",":"))[:180000]}
 ]}
req=urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",
 data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
try:
    with urllib.request.urlopen(req,timeout=120) as resp: raw=json.loads(resp.read().decode())
    content=raw["choices"][0]["message"].get("content","")
    try: review=json.loads(content)
    except Exception: review={"verdict":"HOLD","raw_advisory":content}
    result={"status":"OK","model":MODEL,"advisory_only":True,"review":review}
except Exception as e:
    result={"status":"NVIDIA_CALL_FAILED","model":MODEL,"advisory_only":True,"error":str(e)}
out.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
