"""Leakage-aware, regime-conditioned empirical forecasts for AUREON research.

This is a research component, not an execution adapter or profitability claim.
Input bars must be chronological and contain completed OHLC candles. At forecast
index i, training labels are only admitted when their full horizon ends before i.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Feature:
    momentum_bucket: str
    volatility_bucket: str
    atr: float
    momentum_3_atr: float
    momentum_12_atr: float
    volatility_ratio: float


@dataclass(frozen=True)
class Forecast:
    status: str
    index: int
    horizon_bars: int
    regime: str
    probabilities: dict[str, float]
    expected_return: float | None
    expected_move_atr: float | None
    samples: int
    conditional_samples: int
    confidence: float | None
    reasons: list[str]
    research_only: bool = True
    execution_authorized: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _validate_bars(bars: Sequence[Mapping[str, object]]) -> None:
    if len(bars) < 40:
        raise ValueError("At least 40 chronological bars are required.")
    previous_time = None
    for i, bar in enumerate(bars):
        missing = [k for k in ("high", "low", "close") if k not in bar]
        if missing:
            raise ValueError(f"Bar {i} missing required fields: {missing}")
        high, low, close = (float(bar[k]) for k in ("high", "low", "close"))
        if not all(math.isfinite(x) and x > 0 for x in (high, low, close)):
            raise ValueError(f"Bar {i} has invalid OHLC values.")
        if high < low or close > high or close < low:
            raise ValueError(f"Bar {i} violates OHLC geometry.")
        stamp = bar.get("time")
        if stamp is not None:
            if previous_time is not None and str(stamp) <= str(previous_time):
                raise ValueError("Bars must be strictly chronological by time.")
            previous_time = stamp


def _features(bars: Sequence[Mapping[str, object]], i: int) -> Feature | None:
    if i < 21:
        return None
    close = [float(b["close"]) for b in bars]
    high = [float(b["high"]) for b in bars]
    low = [float(b["low"]) for b in bars]
    tr = []
    for k in range(i - 19, i + 1):
        prev = close[k - 1]
        tr.append(max(high[k] - low[k], abs(high[k] - prev), abs(low[k] - prev)))
    atr = sum(tr) / len(tr)
    if not math.isfinite(atr) or atr <= 0:
        return None
    m3 = (close[i] - close[i - 3]) / atr
    m12 = (close[i] - close[i - 12]) / atr
    short_vol = atr
    long_tr = []
    for k in range(i - 39, i + 1):
        prev = close[k - 1]
        long_tr.append(max(high[k] - low[k], abs(high[k] - prev), abs(low[k] - prev)))
    long_atr = sum(long_tr) / len(long_tr)
    ratio = short_vol / long_atr if long_atr > 0 else 1.0
    mom_bucket = "down" if m3 < -0.35 else "up" if m3 > 0.35 else "flat"
    vol_bucket = "low" if ratio < 0.75 else "high" if ratio > 1.35 else "normal"
    return Feature(mom_bucket, vol_bucket, atr, m3, m12, ratio)


def _regime(feature: Feature) -> str:
    if feature.volatility_ratio > 1.5:
        return "volatility_expansion"
    if feature.volatility_ratio < 0.65:
        return "volatility_compression"
    if abs(feature.momentum_12_atr) > 2.0:
        return "directional_trend"
    return "balanced_or_range"


def forecast(
    bars: Sequence[Mapping[str, object]],
    index: int | None = None,
    horizon_bars: int = 5,
    lookback: int = 1500,
    min_samples: int = 60,
    cost_bps: float = 0.0,
    min_directional_probability: float = 0.55,
    prior_strength: float = 20.0,
) -> Forecast:
    """Estimate empirical UP/DOWN/NEUTRAL probabilities from past analogues only.

    Cost threshold is a return fraction expressed in basis points. Probabilities
    are smoothed toward the historical global class prior. The returned status
    abstains when sample size or directional evidence is inadequate.
    """
    _validate_bars(bars)
    if horizon_bars < 1 or lookback < 1 or min_samples < 1:
        raise ValueError("horizon_bars, lookback and min_samples must be positive.")
    if not _finite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be finite and non-negative.")
    if not 0.0 < min_directional_probability < 1.0 or prior_strength < 0:
        raise ValueError("Invalid probability threshold or prior strength.")
    i = len(bars) - 1 if index is None else index
    if i < 40 or i >= len(bars):
        raise ValueError("index must identify an available bar at index >= 40.")
    current = _features(bars, i)
    if current is None:
        raise ValueError("Unable to compute current features.")
    classes = ("UP", "DOWN", "NEUTRAL")
    threshold = float(cost_bps) / 10000.0
    start = max(40, i - lookback)
    labelled = []
    for j in range(start, i):
        # Strict purge: the complete outcome horizon must end before forecast bar i.
        if j + horizon_bars >= i:
            continue
        feat = _features(bars, j)
        if feat is None:
            continue
        ret = float(bars[j + horizon_bars]["close"]) / float(bars[j]["close"]) - 1.0
        label = "UP" if ret > threshold else "DOWN" if ret < -threshold else "NEUTRAL"
        labelled.append((feat, label, ret))
    if not labelled:
        return Forecast("ABSTAIN", i, horizon_bars, _regime(current),
                        {c: 1 / 3 for c in classes}, None, None, 0, 0, None,
                        ["NO_PAST_LABELLED_SAMPLES"])

    global_counts = {c: sum(1 for _, label, _ in labelled if label == c) for c in classes}
    total = len(labelled)
    prior = {c: global_counts[c] / total for c in classes}
    analogues = [(f, label, ret) for f, label, ret in labelled
                 if f.momentum_bucket == current.momentum_bucket
                 and f.volatility_bucket == current.volatility_bucket]
    counts = {c: sum(1 for _, label, _ in analogues if label == c) for c in classes}
    n_cond = len(analogues)
    denom = n_cond + prior_strength
    probs = {c: ((counts[c] + prior_strength * prior[c]) / denom
                 if denom > 0 else prior[c]) for c in classes}
    expected_return = (sum(ret for _, _, ret in analogues) / n_cond
                       if n_cond else sum(ret for _, _, ret in labelled) / total)
    confidence = max(probs.values())
    direction_prob = max(probs["UP"], probs["DOWN"])
    reasons = []
    if n_cond < min_samples:
        reasons.append("INSUFFICIENT_CONDITIONAL_SAMPLE")
    if direction_prob < min_directional_probability:
        reasons.append("WEAK_DIRECTIONAL_EVIDENCE")
    if confidence < min_directional_probability:
        reasons.append("LOW_CONFIDENCE")
    status = "RESEARCH_CANDIDATE" if not reasons else "ABSTAIN"
    return Forecast(
        status=status,
        index=i,
        horizon_bars=horizon_bars,
        regime=_regime(current),
        probabilities=probs,
        expected_return=expected_return,
        expected_move_atr=expected_return * float(bars[i]["close"]) / current.atr,
        samples=total,
        conditional_samples=n_cond,
        confidence=confidence,
        reasons=reasons,
    )


def write_json(forecast_result: Forecast, path: str | Path) -> None:
    """Write an auditable single-forecast JSON artifact."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(forecast_result.to_dict(), indent=2), encoding="utf-8")
