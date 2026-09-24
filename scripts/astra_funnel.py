from __future__ import annotations

"""Build an ASTRA setup-funnel report from EA CSV event ledgers."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

STAGES=[
    "ASTRA_SWEEP_RECLAIMED",
    "ASTRA_WAITING_MSS",
    "ASTRA_ENTRY_ZONE_ACTIVE",
    "ASTRA_PENDING_ENTRY",
    "ASTRA_BUILDING",
    "ASTRA_PROTECTED",
    "ASTRA_PARTIAL_EXIT",
    "ASTRA_RUNNER",
    "ASTRA_COMPLETED",
]
TERMINAL={"ASTRA_INVALIDATED","ASTRA_EXPIRED","ASTRA_RISK_REJECTED","ASTRA_COMPLETED"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    event_counts=Counter()
    state_counts=Counter()
    campaigns=defaultdict(set)
    files=0
    rows=0
    for p in sorted(args.root.rglob("*.csv")):
        try:
            with p.open(newline="",encoding="utf-8",errors="ignore") as f:
                reader=csv.DictReader(f)
                if not reader.fieldnames or "event" not in reader.fieldnames:
                    continue
                files+=1
                for r in reader:
                    rows+=1
                    event=(r.get("event") or "").strip()
                    state=(r.get("state") or "").strip()
                    cid=(r.get("campaign_id") or "").strip()
                    if event: event_counts[event]+=1
                    if state: state_counts[state]+=1
                    if cid and state: campaigns[cid].add(state)
        except Exception:
            continue

    reached={}
    for s in STAGES:
        reached[s]=sum(1 for st in campaigns.values() if s in st)
    terminal={s:sum(1 for st in campaigns.values() if s in st) for s in sorted(TERMINAL)}
    total=max(1,len(campaigns))
    payload={
        "files":files,
        "rows":rows,
        "campaigns":len(campaigns),
        "stage_reached":reached,
        "stage_reached_percent":{k:v/total*100 for k,v in reached.items()},
        "terminal_states":terminal,
        "events":dict(event_counts.most_common()),
        "states":dict(state_counts.most_common()),
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"funnel.json").write_text(json.dumps(payload,indent=2))

    lines=["# ASTRA Setup Funnel","",
           f"Ledgers: {files} · Rows: {rows} · Campaigns: {len(campaigns)}","",
           "| Stage | Campaigns reached | Reach % |","|---|---:|---:|"]
    for s in STAGES:
        lines.append(f"| {s} | {reached[s]} | {reached[s]/total*100:.1f}% |")
    lines += ["","## Execution/rejection events","",
              "| Event | Count |","|---|---:|"]
    for k,v in event_counts.most_common():
        lines.append(f"| {k} | {v} |")
    (args.out/"funnel.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))

if __name__=="__main__":
    main()
