"""Run the adaptive prediction lab against canonical XAUUSD parquet bars.

Research only. The default row cap protects 8 GB Windows systems from accidental
multi-million-row list-of-dictionaries expansion. Use M5/M15 for long histories.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from research.evolution.cost_stress import evaluate_cost_stress
from research.evolution.walk_forward import evaluate_walk_forward

MAX_ROWS_DEFAULT = 1_200_000

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_bars(path: str | Path, side: str = "bid", max_rows: int = MAX_ROWS_DEFAULT) -> tuple[list[dict], dict]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Parquet dataset not found: {source}")
    if side not in {"bid", "ask", "mid"}:
        raise ValueError("side must be bid, ask, or mid")
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    frame = pd.read_parquet(source)
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if len(frame) > max_rows:
        raise ValueError(f"Dataset has {len(frame):,} rows, above safety cap {max_rows:,}. Use canonical M5/M15 bars for long histories or explicitly raise --max-rows after checking available RAM.")
    prefix = f"{side}_"
    required = ["time", *(prefix + name for name in ("high", "low", "close"))]
    if all(name in frame.columns for name in required):
        selected = frame[required].rename(columns={prefix+"high":"high", prefix+"low":"low", prefix+"close":"close"}).copy()
    elif all(name in frame.columns for name in ("time","high","low","close")):
        selected = frame[["time","high","low","close"]].copy()
    else:
        raise ValueError(f"Missing required columns. Expected {required} or time/high/low/close.")
    selected["time"] = pd.to_datetime(selected["time"], utc=True, errors="raise")
    selected = selected.sort_values("time", kind="stable")
    if selected["time"].duplicated().any():
        raise ValueError("Dataset contains duplicate timestamps; repair canonical data before research.")
    for col in ("high","low","close"):
        selected[col] = pd.to_numeric(selected[col], errors="raise")
    if selected[["high","low","close"]].isna().any().any():
        raise ValueError("Dataset contains null prices.")
    valid = ((selected["high"] >= selected["low"]) & (selected["close"] <= selected["high"]) & (selected["close"] >= selected["low"]) & (selected["low"] > 0))
    if not valid.all():
        raise ValueError("Dataset violates OHLC geometry or positive-price constraints.")
    bars = [{"time": row.time.isoformat(), "high": float(row.high), "low": float(row.low), "close": float(row.close)} for row in selected.itertuples(index=False)]
    metadata = {
        "source_file": str(source),
        "source_sha256": _sha256_file(source),
        "rows": len(bars),
        "first_time_utc": bars[0]["time"] if bars else None,
        "last_time_utc": bars[-1]["time"] if bars else None,
        "price_side": side,
    }
    return bars, metadata

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="Canonical XAUUSD timeframe parquet file")
    ap.add_argument("--out", default="research_results/adaptive_lab")
    ap.add_argument("--side", choices=("bid","ask","mid"), default="bid")
    ap.add_argument("--max-rows", type=int, default=MAX_ROWS_DEFAULT)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--stride", type=int, default=60, help="Must be >= horizon; larger is faster")
    ap.add_argument("--lookback", type=int, default=1500)
    ap.add_argument("--min-samples", type=int, default=60)
    ap.add_argument("--start-index", type=int, default=None)
    ap.add_argument("--end-index", type=int, default=None)
    ap.add_argument("--cost-bps", type=float, default=8.0)
    ap.add_argument("--cost-grid-bps", default="4,8,12,20")
    args = ap.parse_args()
    bars, source = load_bars(args.data, args.side, args.max_rows)
    costs = [float(part.strip()) for part in args.cost_grid_bps.split(",") if part.strip()]
    common = {"horizon_bars":args.horizon, "stride":args.stride, "lookback":args.lookback, "min_samples":args.min_samples, "start_index":args.start_index, "end_index":args.end_index}
    walk = evaluate_walk_forward(bars, cost_bps=args.cost_bps, **common)
    stress = evaluate_cost_stress(bars, cost_scenarios_bps=costs, **common)
    report = {
        "schema":"aureon.adaptive_lab.v1",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":source,
        "configuration":{**common,"cost_bps":args.cost_bps,"cost_grid_bps":costs},
        "walk_forward":walk,
        "cost_stress":stress,
        "authority":{"research_only":True,"execution_authorized":False,"demo_orders_submitted":False,"live_trading_allowed":False},
        "data_fidelity":{"price_data":"OHLC_BAR_PROXY","real_tick_archive_consumed":False,"native_mt5_strategy_tester_validation":"NOT_RUN","promotion_blocked_until_real_tick_test":True},
        "promotion_gate":"BLOCKED: OHLC proxy only; requires native MT5 real-tick verification and frozen-control comparison",
    }
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "adaptive_lab_report.json"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"report":str(report_path),"source":source,"forecast_count":walk["forecast_count"],"coverage":walk["coverage"],"brier_score":walk["brier_score"],"prior_baseline_brier_score":walk["prior_baseline_brier_score"],"proxy_net_return_sum":walk["proxy_net_return_sum"],"proxy_max_drawdown":walk["proxy_max_drawdown"],"research_only":True,"execution_authorized":False}, indent=2))

if __name__ == "__main__":
    main()
