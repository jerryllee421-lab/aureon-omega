"""Causal, auditable strategy-context scoring for XAUUSD research.

This is deterministic feature scoring, not machine learning and not an order engine.
All context features use current/completed bars and past-only rolling windows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def score_candidates(features: pd.DataFrame, *, min_score: float = 3.0,
                     min_margin: float = 1.0) -> pd.DataFrame:
    """Score long/short hypotheses, classify regime, and abstain on weak conflicts.

    Required columns come from smc_intraday_candidates.build_candidates().
    Scores are evidence counts/weights for ranking research candidates, not
    probabilities. No score is allowed to override missing data or bad costs.
    """
    required = {
        "open", "high", "low", "close", "atr", "bos_up", "bos_down",
        "choch_up", "choch_down", "displacement_up", "displacement_down",
        "buy_side_sweep_reclaim", "sell_side_sweep_reclaim",
        "near_support", "near_resistance", "bullish_engulfing",
        "bearish_engulfing", "pinbar_up", "pinbar_down",
        "trendline_break_up", "trendline_break_down",
    }
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"missing candidate features: {sorted(missing)}")
    if not 0 <= min_score <= 20 or not 0 <= min_margin <= 20:
        raise ValueError("score thresholds must be between 0 and 20")
    x = features.copy().sort_index()
    if x.index.has_duplicates:
        raise ValueError("index must be unique")
    if not x.index.is_monotonic_increasing:
        raise ValueError("index must be chronological")
    for c in ("open", "high", "low", "close", "atr"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    if (x.high < x[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("invalid OHLC")
    if (x.low > x[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("invalid OHLC")

    close = x.close
    # All reference values are lagged: no current-bar leakage into the baseline.
    ema_fast = close.ewm(span=20, adjust=False, min_periods=20).mean()
    ema_slow = close.ewm(span=50, adjust=False, min_periods=50).mean()
    slope = ema_fast.diff(3)
    prior_atr_median = x.atr.shift(1).rolling(100, min_periods=30).median()
    x["trend_regime"] = np.select(
        [(ema_fast > ema_slow) & (slope > 0),
         (ema_fast < ema_slow) & (slope < 0)],
        ["UPTREND", "DOWNTREND"], default="MIXED"
    )
    x["volatility_regime"] = np.select(
        [x.atr > prior_atr_median * 1.5,
         x.atr < prior_atr_median * 0.7],
        ["EXPANSION", "COMPRESSION"], default="NORMAL"
    )

    long_score = pd.Series(0.0, index=x.index)
    short_score = pd.Series(0.0, index=x.index)
    # Structural evidence receives most weight; pattern-only evidence is weak.
    def add(col, weight, long=True, short=True):
        nonlocal long_score, short_score
        flag = x[col].fillna(False).astype(bool)
        if long:
            long_score = long_score + flag.astype(float) * weight
        if short:
            short_score = short_score + flag.astype(float) * weight

    add("bos_up", 1.5, short=False)
    add("choch_up", 2.0, short=False)
    add("displacement_up", 1.0, short=False)
    add("sell_side_sweep_reclaim", 2.0, short=False)
    add("near_support", 0.5, short=False)
    add("bullish_engulfing", 0.5, short=False)
    add("pinbar_up", 0.5, short=False)
    add("trendline_break_up", 1.0, short=False)
    add("bos_down", 1.5, long=False)
    add("choch_down", 2.0, long=False)
    add("displacement_down", 1.0, long=False)
    add("buy_side_sweep_reclaim", 2.0, long=False)
    add("near_resistance", 0.5, long=False)
    add("bearish_engulfing", 0.5, long=False)
    add("pinbar_down", 0.5, long=False)
    add("trendline_break_down", 1.0, long=False)

    long_score += (x.trend_regime == "UPTREND").astype(float) * 0.75
    short_score += (x.trend_regime == "DOWNTREND").astype(float) * 0.75
    # Compression suppresses breakout confidence until a displacement confirms.
    compression = x.volatility_regime == "COMPRESSION"
    long_score -= (compression & ~x.displacement_up.fillna(False).astype(bool)).astype(float) * 0.5
    short_score -= (compression & ~x.displacement_down.fillna(False).astype(bool)).astype(float) * 0.5

    x["long_score"] = long_score
    x["short_score"] = short_score
    x["score_margin"] = (long_score - short_score).abs()
    enough_data = x.atr.notna() & ema_slow.notna() & prior_atr_median.notna()
    long_ok = (long_score >= min_score) & ((long_score - short_score) >= min_margin)
    short_ok = (short_score >= min_score) & ((short_score - long_score) >= min_margin)
    x["decision"] = np.select(
        [~enough_data, long_ok, short_ok],
        ["ABSTAIN_WARMUP", "RESEARCH_LONG_CANDIDATE", "RESEARCH_SHORT_CANDIDATE"],
        default="ABSTAIN_WEAK_OR_CONFLICTING"
    )
    x["candidate_strength"] = np.maximum(long_score, short_score)
    x["research_only"] = True
    x["trade_authorized"] = False
    return x
