"""Execution-cost sensitivity wrapper for AUREON walk-forward research."""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from research.evolution.walk_forward import evaluate_walk_forward


def evaluate_cost_stress(
    bars: Sequence[Mapping[str, object]],
    *,
    cost_scenarios_bps: Sequence[float] = (4.0, 8.0, 12.0, 20.0),
    horizon_bars: int = 5,
    stride: int = 20,
    lookback: int = 1500,
    min_samples: int = 60,
    min_directional_probability: float = 0.55,
    prior_strength: float = 20.0,
    start_index: int | None = None,
    end_index: int | None = None,
) -> dict:
    """Run identical chronological evaluation under multiple flat cost floors."""
    costs = [float(x) for x in cost_scenarios_bps]
    if not costs or any(not math.isfinite(x) or x < 0 for x in costs):
        raise ValueError("Provide one or more finite non-negative cost scenarios.")
    if len(set(costs)) != len(costs):
        raise ValueError("Cost scenarios must be unique.")
    results = []
    for cost in sorted(costs):
        result = evaluate_walk_forward(
            bars,
            horizon_bars=horizon_bars,
            stride=stride,
            lookback=lookback,
            min_samples=min_samples,
            cost_bps=cost,
            min_directional_probability=min_directional_probability,
            prior_strength=prior_strength,
            start_index=start_index,
            end_index=end_index,
        )
        results.append({
            "cost_bps": cost,
            "brier_score": result["brier_score"],
            "log_loss": result["log_loss"],
            "coverage": result["coverage"],
            "proxy_trade_count": result["proxy_trade_count"],
            "proxy_win_rate": result["proxy_win_rate"],
            "proxy_profit_factor": result["proxy_profit_factor"],
            "proxy_net_return_sum": result["proxy_net_return_sum"],
            "proxy_max_drawdown": result["proxy_max_drawdown"],
            "prior_baseline_brier_score": result["prior_baseline_brier_score"],
        })
    net_returns = [row["proxy_net_return_sum"] for row in results]
    return {
        "research_only": True,
        "execution_authorized": False,
        "method": "same_forecast_schedule_multiple_flat_cost_floors",
        "scenarios": results,
        "net_return_range": {
            "best": max(net_returns),
            "worst": min(net_returns),
            "degradation_best_to_worst": max(net_returns) - min(net_returns),
        },
        "warning": (
            "Flat basis-point costs are a sensitivity proxy, not a broker-specific "
            "spread/slippage model. Forecast class labels are re-evaluated at each "
            "cost floor; use identical settings and preserve an untouched holdout."
        ),
    }
