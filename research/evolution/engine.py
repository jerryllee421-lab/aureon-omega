from __future__ import annotations
import argparse, hashlib, json, math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import yaml

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def metric(d, *names, default=None):
    for n in names:
        if isinstance(d, dict) and n in d and d[n] is not None:
            return d[n]
    return default

def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False

@dataclass
class Verdict:
    status: str
    failures: list[str]
    gates: dict
    next_action: str

def classify(report, policy):
    p = policy["promotion"]
    base = report.get("baseline", report)
    hold = report.get("holdout", {})
    trades = metric(hold, "trades", "total_trades", default=metric(base, "trades", "total_trades", default=0))
    pf = metric(hold, "profit_factor", "pf", default=metric(base, "profit_factor", "pf", default=0))
    exp = metric(hold, "expectancy_r", "expectancy", default=metric(base, "expectancy_r", "expectancy", default=0))
    dd = metric(hold, "max_drawdown_r", "drawdown_r", default=metric(base, "max_drawdown_r", "drawdown_r", default=999))
    degradation = metric(report, "oos_degradation_pct", default=0)
    gates = {
        "sample": finite(trades) and float(trades) >= p["min_trades"],
        "profit_factor": finite(pf) and float(pf) >= p["min_profit_factor"],
        "expectancy": finite(exp) and float(exp) >= p["min_expectancy_r"],
        "drawdown": finite(dd) and float(dd) <= p["max_drawdown_r"],
        "oos_degradation": finite(degradation) and float(degradation) <= p["max_oos_degradation_pct"],
        "holdout_positive": (not p["require_positive_holdout"]) or (finite(exp) and float(exp) > 0),
    }
    failures = []
    if not gates["sample"]: failures.append("INSUFFICIENT_SAMPLE")
    if not gates["profit_factor"] or not gates["expectancy"]: failures.append("NO_EDGE")
    if not gates["drawdown"]: failures.append("EXCESSIVE_DD")
    if not gates["oos_degradation"] or not gates["holdout_positive"]: failures.append("OOS_COLLAPSE")
    for flag, code in [
        ("parameter_cliff", "PARAMETER_CLIFF"),
        ("tail_winner_dependent", "TAIL_WINNER_DEPENDENT"),
        ("spread_sensitive", "SPREAD_SENSITIVE"),
        ("slippage_sensitive", "SLIPPAGE_SENSITIVE"),
    ]:
        if report.get(flag) is True: failures.append(code)
    failures = list(dict.fromkeys(failures))
    status = "PROMOTE_TO_ROBUSTNESS" if all(gates.values()) and not failures else "REJECT_OR_REPAIR"
    action = "run_neighbor_walkforward_cost_stress" if status.startswith("PROMOTE") else "diagnose_and_mutate_max_2_variables"
    return Verdict(status, failures, gates, action)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--policy", default="research/evolution/policy.yml")
    ap.add_argument("--ledger", default="research_results/evolution_ledger.jsonl")
    ap.add_argument("--out", default="research_results/evolution_verdict.json")
    ap.add_argument("--commit", default="unknown")
    a = ap.parse_args()
    policy = yaml.safe_load(Path(a.policy).read_text())
    report = load_json(a.report)
    verdict = classify(report, policy)
    raw = Path(a.report).read_bytes()
    record = {
        "schema": "aureon.evolution.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": a.commit,
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "control": policy["immutable"]["historical_control"],
        "verdict": asdict(verdict),
        "note": "Research evidence only. No real-money execution authorization.",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(record, indent=2))
    with open(a.ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(json.dumps(record, indent=2))

if __name__ == "__main__":
    main()
