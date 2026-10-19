"""Leakage-aware walk-forward evaluation for the AUREON research predictor.

This evaluator does not submit orders. Results are historical research metrics,
not a promise of future performance. It uses sparse forecasts and bounded windows
to avoid repeatedly scanning the full dataset.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Mapping, Sequence

from research.evolution.adaptive_prediction import forecast

CLASSES = ("UP", "DOWN", "NEUTRAL")


def _label(ret: float, cost_fraction: float) -> str:
    return "UP" if ret > cost_fraction else "DOWN" if ret < -cost_fraction else "NEUTRAL"


def _brier(probabilities: Mapping[str, float], actual: str) -> float:
    return sum((float(probabilities[c]) - (1.0 if c == actual else 0.0)) ** 2 for c in CLASSES)


def _log_loss(probabilities: Mapping[str, float], actual: str) -> float:
    p = min(1.0 - 1e-12, max(1e-12, float(probabilities[actual])))
    return -math.log(p)


def evaluate_walk_forward(
    bars: Sequence[Mapping[str, object]],
    *,
    horizon_bars: int = 5,
    stride: int = 5,
    lookback: int = 1500,
    min_samples: int = 60,
    cost_bps: float = 8.0,
    min_directional_probability: float = 0.55,
    prior_strength: float = 20.0,
    start_index: int | None = None,
    end_index: int | None = None,
) -> dict:
    """Evaluate forecasts chronologically using only the history available then."""
    if horizon_bars < 1 or stride < horizon_bars or lookback < 100:
        raise ValueError("Require positive horizon, stride >= horizon, and lookback >= 100.")
    if not math.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be finite and non-negative.")
    n = len(bars)
    start = max(80, horizon_bars + 40) if start_index is None else max(80, start_index)
    end = n - horizon_bars if end_index is None else min(end_index, n - horizon_bars)
    if end <= start:
        raise ValueError("Insufficient bars for the requested evaluation range.")

    cost_fraction = cost_bps / 10000.0
    forecasts = abstained = correct = directional_n = 0
    brier_sum = logloss_sum = baseline_brier_sum = baseline_logloss_sum = 0.0
    predicted_counts = defaultdict(int)
    actual_counts = defaultdict(int)
    regime_stats = defaultdict(lambda: {"n": 0, "brier_sum": 0.0, "logloss_sum": 0.0})
    pnl = []
    proxy_trade_count = 0
    equity = peak = max_drawdown = 0.0

    for i in range(start, end, stride):
        # Bounded prefix only: future bars are never passed to the predictor.
        left = max(0, i - lookback - 40)
        history = bars[left:i + 1]
        f = forecast(
            history,
            index=len(history) - 1,
            horizon_bars=horizon_bars,
            lookback=min(lookback, len(history) - 40),
            min_samples=min_samples,
            cost_bps=cost_bps,
            min_directional_probability=min_directional_probability,
            prior_strength=prior_strength,
        )
        future_ret = float(bars[i + horizon_bars]["close"]) / float(bars[i]["close"]) - 1.0
        actual = _label(future_ret, cost_fraction)
        actual_counts[actual] += 1
        forecasts += 1
        score = _brier(f.probabilities, actual)
        loss = _log_loss(f.probabilities, actual)
        brier_sum += score
        logloss_sum += loss

        # Baseline class prior only uses outcomes fully observable at timestamp i.
        prior_start = max(40, i - lookback)
        past_labels = []
        for j in range(prior_start, i - horizon_bars):
            ret = float(bars[j + horizon_bars]["close"]) / float(bars[j]["close"]) - 1.0
            past_labels.append(_label(ret, cost_fraction))
        if past_labels:
            base_probs = {c: (past_labels.count(c) + 1.0) / (len(past_labels) + 3.0) for c in CLASSES}
        else:
            base_probs = {c: 1.0 / 3.0 for c in CLASSES}
        baseline_brier_sum += _brier(base_probs, actual)
        baseline_logloss_sum += _log_loss(base_probs, actual)

        predicted = max(CLASSES, key=lambda c: f.probabilities[c])
        predicted_counts[predicted] += 1
        if predicted in ("UP", "DOWN") and actual in ("UP", "DOWN"):
            directional_n += 1
            correct += int(predicted == actual)

        rs = regime_stats[f.regime]
        rs["n"] += 1
        rs["brier_sum"] += score
        rs["logloss_sum"] += loss

        # Research-only directional proxy. No broker execution is performed.
        trade_pnl = 0.0
        if f.status == "RESEARCH_CANDIDATE" and predicted in ("UP", "DOWN"):
            proxy_trade_count += 1
            trade_pnl = (future_ret if predicted == "UP" else -future_ret) - cost_fraction
        pnl.append(trade_pnl)
        equity += trade_pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if f.status == "ABSTAIN":
            abstained += 1

    traded = [x for x in pnl if x != 0.0]
    trade_count = proxy_trade_count
    wins = sum(1 for x in pnl if x > 0)
    gross_profit = sum(x for x in pnl if x > 0)
    gross_loss = -sum(x for x in pnl if x < 0)
    per_regime = {
        regime: {
            "samples": v["n"],
            "brier_score": v["brier_sum"] / v["n"],
            "log_loss": v["logloss_sum"] / v["n"],
        }
        for regime, v in sorted(regime_stats.items())
    }
    return {
        "research_only": True,
        "execution_authorized": False,
        "method": "walk_forward_sparse_non_overlapping_horizons",
        "horizon_bars": horizon_bars,
        "stride": stride,
        "cost_bps_assumption": cost_bps,
        "forecast_count": forecasts,
        "abstain_count": abstained,
        "coverage": (forecasts - abstained) / forecasts if forecasts else 0.0,
        "brier_score": brier_sum / forecasts if forecasts else None,
        "log_loss": logloss_sum / forecasts if forecasts else None,
        "prior_baseline_brier_score": baseline_brier_sum / forecasts if forecasts else None,
        "prior_baseline_log_loss": baseline_logloss_sum / forecasts if forecasts else None,
        "directional_accuracy_when_directional": correct / directional_n if directional_n else None,
        "directional_evaluations": directional_n,
        "predicted_class_counts": dict(predicted_counts),
        "actual_class_counts": dict(actual_counts),
        "proxy_trade_count": trade_count,
        "proxy_win_rate": wins / trade_count if trade_count else None,
        "proxy_profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "proxy_net_return_sum": sum(pnl),
        "proxy_max_drawdown": max_drawdown,
        "regime_metrics": per_regime,
        "warning": "Close-to-close proxy with flat cost floor; not a native tick backtest.",
    }
