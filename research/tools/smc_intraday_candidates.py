"""Causal XAUUSD SMC and intraday setup labels for research.

Input must be chronological OHLC bars indexed by timestamp. Swings are confirmed
only after right_bars future candles have closed; the resulting level is made
available at confirmation time, not retroactively at the pivot candle.
This module emits research labels, not orders or profitability claims.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED = {"open", "high", "low", "close"}


def build_candidates(
    bars: pd.DataFrame,
    *,
    left_bars: int = 3,
    right_bars: int = 2,
    sr_lookback: int = 30,
    atr_period: int = 14,
    displacement_atr: float = 1.0,
    trendline_lookback: int = 40,
) -> pd.DataFrame:
    """Return causal structure, pattern and support/resistance candidate columns.

    Output includes:
      swing_high/low (confirmation-time events), bos_up/down, choch_up/down,
      bullish/bearish_engulfing, pinbar_up/down, support/resistance proximity,
      trendline_break_up/down, displacement_up/down, and long/short candidate
      labels. Candidate labels are deliberately unfiltered research hypotheses.
    """
    if not REQUIRED.issubset(bars.columns):
        raise ValueError(f"bars must include {sorted(REQUIRED)}")
    if left_bars < 1 or right_bars < 1 or sr_lookback < 3 or atr_period < 2:
        raise ValueError("invalid lookback parameters")
    x = bars.copy().sort_index()
    if x.index.has_duplicates:
        raise ValueError("bar index must be unique")
    for c in REQUIRED:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=list(REQUIRED))
    if (x.high < x[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("invalid OHLC: high below another candle field")
    if (x.low > x[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("invalid OHLC: low above another candle field")

    prev_close = x.close.shift(1)
    tr = pd.concat([
        x.high - x.low,
        (x.high - prev_close).abs(),
        (x.low - prev_close).abs(),
    ], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / atr_period, adjust=False, min_periods=atr_period).mean()

    n = len(x)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    # A pivot at p is only announced at p + right_bars. No backdating.
    for p in range(left_bars, n - right_bars):
        hi = x.high.iloc[p-left_bars:p+right_bars+1]
        lo = x.low.iloc[p-left_bars:p+right_bars+1]
        if x.high.iloc[p] == hi.max() and int((hi == x.high.iloc[p]).sum()) == 1:
            sh[p + right_bars] = float(x.high.iloc[p])
        if x.low.iloc[p] == lo.min() and int((lo == x.low.iloc[p]).sum()) == 1:
            sl[p + right_bars] = float(x.low.iloc[p])
    x["swing_high"] = sh
    x["swing_low"] = sl

    last_sh = np.full(n, np.nan)
    last_sl = np.full(n, np.nan)
    curr_h = curr_l = np.nan
    for i in range(n):
        if np.isfinite(sh[i]):
            curr_h = sh[i]
        if np.isfinite(sl[i]):
            curr_l = sl[i]
        last_sh[i], last_sl[i] = curr_h, curr_l
    x["last_confirmed_swing_high"] = last_sh
    x["last_confirmed_swing_low"] = last_sl

    prev_h = pd.Series(last_sh, index=x.index).shift(1)
    prev_l = pd.Series(last_sl, index=x.index).shift(1)
    x["bos_up"] = (prev_h.notna() & (x.close > prev_h) & (x.close.shift(1) <= prev_h)).fillna(False)
    x["bos_down"] = (prev_l.notna() & (x.close < prev_l) & (x.close.shift(1) >= prev_l)).fillna(False)

    # Track last structural break direction. CHoCH is a break against that state.
    state = 0
    choch_up, choch_down = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    for i in range(n):
        bu, bd = bool(x.bos_up.iloc[i]), bool(x.bos_down.iloc[i])
        if bu:
            choch_up[i] = state == -1
            state = 1
        elif bd:
            choch_down[i] = state == 1
            state = -1
    x["choch_up"], x["choch_down"] = choch_up, choch_down

    body = (x.close - x.open).abs()
    rng = (x.high - x.low).replace(0, np.nan)
    upper = x.high - x[["open", "close"]].max(axis=1)
    lower = x[["open", "close"]].min(axis=1) - x.low
    x["bullish_engulfing"] = (
        (x.close > x.open) & (x.close.shift(1) < x.open.shift(1)) &
        (x.open <= x.close.shift(1)) & (x.close >= x.open.shift(1))
    ).fillna(False)
    x["bearish_engulfing"] = (
        (x.close < x.open) & (x.close.shift(1) > x.open.shift(1)) &
        (x.open >= x.close.shift(1)) & (x.close <= x.open.shift(1))
    ).fillna(False)
    x["pinbar_up"] = ((lower >= 2 * body) & (upper <= body) & (x.close > x.open)).fillna(False)
    x["pinbar_down"] = ((upper >= 2 * body) & (lower <= body) & (x.close < x.open)).fillna(False)
    x["displacement_up"] = ((x.close > x.open) & (body >= displacement_atr * x.atr)).fillna(False)
    x["displacement_down"] = ((x.close < x.open) & (body >= displacement_atr * x.atr)).fillna(False)

    # Prior-window levels exclude the current candle to avoid self-referential S/R.
    x["support"] = x.low.shift(1).rolling(sr_lookback, min_periods=sr_lookback).min()
    x["resistance"] = x.high.shift(1).rolling(sr_lookback, min_periods=sr_lookback).max()
    tol = x.atr * 0.25
    x["near_support"] = ((x.close - x.support).abs() <= tol).fillna(False)
    x["near_resistance"] = ((x.close - x.resistance).abs() <= tol).fillna(False)

    # Linear trendlines fit only prior confirmed swing points. Break evaluated on close.
    tl_up, tl_down = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    lows = x.swing_low.to_numpy()
    highs = x.swing_high.to_numpy()
    closes = x.close.to_numpy()
    for i in range(n):
        start = max(0, i - trendline_lookback)
        low_points = [(j, lows[j]) for j in range(start, i) if np.isfinite(lows[j])]
        high_points = [(j, highs[j]) for j in range(start, i) if np.isfinite(highs[j])]
        if len(low_points) >= 2:
            (a, va), (b, vb) = low_points[-2:]
            if b > a:
                projected = va + (vb - va) * (i - a) / (b - a)
                tl_up[i] = closes[i] > projected and (i == 0 or closes[i-1] <= va + (vb-va)*(i-1-a)/(b-a))
        if len(high_points) >= 2:
            (a, va), (b, vb) = high_points[-2:]
            if b > a:
                projected = va + (vb - va) * (i - a) / (b - a)
                tl_down[i] = closes[i] < projected and (i == 0 or closes[i-1] >= va + (vb-va)*(i-1-a)/(b-a))
    x["trendline_break_up"], x["trendline_break_down"] = tl_up, tl_down

    # Liquidity sweep/reclaim: only levels confirmed before the current bar.
    # Sweeping a prior high then closing below it is a bearish (buy-side) sweep;
    # sweeping a prior low then closing above it is a bullish (sell-side) sweep.
    x["buy_side_sweep_reclaim"] = (
        prev_h.notna() & (x.high > prev_h) & (x.close < prev_h)
    ).fillna(False)
    x["sell_side_sweep_reclaim"] = (
        prev_l.notna() & (x.low < prev_l) & (x.close > prev_l)
    ).fillna(False)

    # Separate raw setup families so they can be ablated independently.
    x["smc_long"] = (x.choch_up | x.bos_up) & x.displacement_up
    x["smc_short"] = (x.choch_down | x.bos_down) & x.displacement_down
    x["sweep_reclaim_long"] = x.sell_side_sweep_reclaim & (x.displacement_up | x.choch_up)
    x["sweep_reclaim_short"] = x.buy_side_sweep_reclaim & (x.displacement_down | x.choch_down)
    x["sr_reversal_long"] = x.near_support & (x.pinbar_up | x.bullish_engulfing)
    x["sr_reversal_short"] = x.near_resistance & (x.pinbar_down | x.bearish_engulfing)
    x["trendline_long"] = x.trendline_break_up & x.displacement_up
    x["trendline_short"] = x.trendline_break_down & x.displacement_down
    x["pattern_long"] = x.bullish_engulfing | x.pinbar_up
    x["pattern_short"] = x.bearish_engulfing | x.pinbar_down
    x["candidate_long"] = x.smc_long | x.sweep_reclaim_long | x.sr_reversal_long | x.trendline_long
    x["candidate_short"] = x.smc_short | x.sweep_reclaim_short | x.sr_reversal_short | x.trendline_short
    return x
