"""Restart-durable canary state and append-only evidence ledger."""
import json, os, time
from dataclasses import dataclass, asdict

@dataclass
class CanaryState:
    completed:int=0
    open_position_id:str=""
    halted:bool=False
    halt_reason:str=""

class StateStore:
    def __init__(self,path="state/canary.json",ledger="state/evidence.jsonl",limit=5):
        self.path=path; self.ledger=ledger; self.limit=limit
        os.makedirs(os.path.dirname(path),exist_ok=True)
    def load(self):
        try:
            with open(self.path) as f:return CanaryState(**json.load(f))
        except FileNotFoundError:return CanaryState()
    def save(self,s):
        if s.completed>=self.limit:
            s.halted=True; s.halt_reason="CANARY_LIMIT_REACHED"
        tmp=self.path+".tmp"
        with open(tmp,"w") as f: json.dump(asdict(s),f,sort_keys=True)
        os.replace(tmp,self.path)
    def evidence(self,event,**fields):
        row={"ts":time.time(),"event":event,**fields}
        with open(self.ledger,"a") as f:f.write(json.dumps(row,sort_keys=True)+"\n")
    def reconcile(self,broker_open_ids):
        s=self.load()
        if s.open_position_id and s.open_position_id not in {str(x) for x in broker_open_ids}:
            s.halted=True; s.halt_reason="STATE_MISMATCH"
            self.evidence("RECONCILIATION_FAIL",local_position=s.open_position_id)
            self.save(s)
        return s
    def record_close(self,position_id,**metrics):
        s=self.load()
        if s.open_position_id and str(position_id)!=s.open_position_id:
            s.halted=True;s.halt_reason="CLOSE_ID_MISMATCH";self.save(s);return s
        s.open_position_id="";s.completed+=1
        self.evidence("TRADE_CLOSED",position_id=str(position_id),completed=s.completed,**metrics)
        self.save(s);return s
