from __future__ import annotations

"""AUREON Ω / ASTRA QEDGE multi-strategy Gold research engine.

Purpose
-------
Research several *independent* deterministic XAUUSD strategy families on the
same pinned bid/ask M1 dataset and across several coherent timeframe cascades.

This is a research engine, not an execution engine. It uses causal closed-bar
signals, independent campaign accounting and R-normalized outcomes. Broker
native MT5 confirmation remains mandatory before any forward-demo promotion.

Data contract
-------------
research_data/XAUUSD/M1/year=YYYY/month=MM/bars.parquet with columns:
time, bid_open/high/low/close, ask_open/high/low/close.

Execution convention
--------------------
- Signals are formed only from completed bars.
- Market entries occur at the next execution bar open.
- BUY entries use ask; SELL entries use bid.
- BUY exits are tested on bid extremes; SELL exits on ask extremes.
- If SL and TP are both touched in the same bar, SL wins (conservative).
- One open campaign per strategy/timeframe variant.
- Primary outcomes are R-multiples, not dollars.
"""

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Cascade:
    name: str
    entry: str
    liquidity: str
    trend: str
    context: str


CASCADES = [
    Cascade("M1_M5_M15_H1", "1min", "5min", "15min", "1h"),
    Cascade("M4_M20_H1_H4", "4min", "20min", "1h", "4h"),
    Cascade("M5_M15_H1_H4", "5min", "15min", "1h", "4h"),
    Cascade("M10_M30_H2_H6", "10min", "30min", "2h", "6h"),
    Cascade("M15_H1_H4_H12", "15min", "1h", "4h", "12h"),
]


@dataclass
class Signal:
    strategy: str
    cascade: str
    direction: int
    signal_time: pd.Timestamp
    level: float
    stop_ref: float
    note: str


@dataclass
class Trade:
    strategy: str
    cascade: str
    direction: int
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    stop: float
    target: float
    exit: float
    initial_risk: float
    r: float
    mfe_r: float
    mae_r: float
    bars: int
    reason: str
    note: str


def load_m1(root: Path) -> pd.DataFrame:
    files = sorted((root / "XAUUSD" / "M1").rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No XAUUSD M1 parquet files under {root}")
    x = pd.concat((pd.read_parquet(p) for p in files), ignore_index=True)
    x["time"] = pd.to_datetime(x["time"], utc=True)
    required = [
        "bid_open", "bid_high", "bid_low", "bid_close",
        "ask_open", "ask_high", "ask_low", "ask_close",
    ]
    missing = [c for c in required if c not in x.columns]
    if missing:
        raise ValueError(f"Missing bid/ask columns: {missing}")
    x = x.sort_values("time").drop_duplicates("time").reset_index(drop=True)

    # Remove market-closed flat filler rows. This matches the existing research
    # harness and avoids manufacturing bars when a terminal would receive none.
    prev_bid = x["bid_close"].shift(1)
    prev_ask = x["ask_close"].shift(1)
    active = (
        (x["bid_high"] > x["bid_low"])
        | (x["ask_high"] > x["ask_low"])
        | (x["bid_close"] != prev_bid)
        | (x["ask_close"] != prev_ask)
    )
    return x.loc[active].reset_index(drop=True)


def resample_bars(m1: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "1min":
        out = m1.copy()
    else:
        q = m1.set_index("time")
        out = pd.DataFrame({
            "bid_open": q["bid_open"].resample(rule, label="right", closed="right").first(),
            "bid_high": q["bid_high"].resample(rule, label="right", closed="right").max(),
            "bid_low": q["bid_low"].resample(rule, label="right", closed="right").min(),
            "bid_close": q["bid_close"].resample(rule, label="right", closed="right").last(),
            "ask_open": q["ask_open"].resample(rule, label="right", closed="right").first(),
            "ask_high": q["ask_high"].resample(rule, label="right", closed="right").max(),
            "ask_low": q["ask_low"].resample(rule, label="right", closed="right").min(),
            "ask_close": q["ask_close"].resample(rule, label="right", closed="right").last(),
        }).dropna().reset_index()
    out["mid_open"] = (out["bid_open"] + out["ask_open"]) / 2.0
    out["mid_high"] = (out["bid_high"] + out["ask_high"]) / 2.0
    out["mid_low"] = (out["bid_low"] + out["ask_low"]) / 2.0
    out["mid_close"] = (out["bid_close"] + out["ask_close"]) / 2.0
    out["spread_close"] = out["ask_close"] - out["bid_close"]
    return out.reset_index(drop=True)


def add_features(x: pd.DataFrame) -> pd.DataFrame:
    y = x.copy()
    prev = y["mid_close"].shift(1)
    tr = pd.concat([
        (y["mid_high"] - y["mid_low"]).abs(),
        (y["mid_high"] - prev).abs(),
        (y["mid_low"] - prev).abs(),
    ], axis=1).max(axis=1)
    y["atr14"] = tr.ewm(alpha=1 / 14.0, adjust=False, min_periods=14).mean()
    for p in (9, 20, 21, 50):
        y[f"ema{p}"] = y["mid_close"].ewm(span=p, adjust=False, min_periods=p).mean()
    y["body"] = (y["mid_close"] - y["mid_open"]).abs()
    y["range"] = (y["mid_high"] - y["mid_low"]).abs()
    y["body_eff"] = y["body"] / y["range"].replace(0, np.nan)
    y["prior_high5"] = y["mid_high"].rolling(5).max().shift(1)
    y["prior_low5"] = y["mid_low"].rolling(5).min().shift(1)
    y["prior_high20"] = y["mid_high"].rolling(20).max().shift(1)
    y["prior_low20"] = y["mid_low"].rolling(20).min().shift(1)
    y["ema50_slope3_atr"] = (y["ema50"] - y["ema50"].shift(3)) / (3 * y["atr14"].replace(0, np.nan))
    movement = y["mid_close"].diff().abs().rolling(20).sum()
    y["efficiency20"] = (y["mid_close"] - y["mid_close"].shift(20)).abs() / movement.replace(0, np.nan)
    return y


def merge_context(base: pd.DataFrame, higher: pd.DataFrame, prefix: str, columns: Iterable[str]) -> pd.DataFrame:
    rhs = higher[["time", *columns]].copy()
    rhs = rhs.rename(columns={c: f"{prefix}_{c}" for c in columns})
    return pd.merge_asof(
        base.sort_values("time"),
        rhs.sort_values("time"),
        on="time",
        direction="backward",
        allow_exact_matches=True,
    )


def build_pack(m1: pd.DataFrame, cascade: Cascade) -> dict[str, pd.DataFrame]:
    rules = {cascade.entry, cascade.liquidity, cascade.trend, cascade.context}
    bars = {r: add_features(resample_bars(m1, r)) for r in rules}
    return {
        "entry": bars[cascade.entry],
        "liq": bars[cascade.liquidity],
        "trend": bars[cascade.trend],
        "context": bars[cascade.context],
    }


def trend_direction(row: pd.Series, prefix: str = "") -> int:
    p = prefix
    close = row.get(f"{p}mid_close")
    e20 = row.get(f"{p}ema20")
    e50 = row.get(f"{p}ema50")
    slope = row.get(f"{p}ema50_slope3_atr")
    eff = row.get(f"{p}efficiency20")
    vals = [close, e20, e50, slope, eff]
    if not all(np.isfinite(v) for v in vals):
        return 0
    if close > e20 > e50 and slope > 0.01 and eff >= 0.18:
        return 1
    if close < e20 < e50 and slope < -0.01 and eff >= 0.18:
        return -1
    return 0


def liquidity_reversal(pack: dict[str, pd.DataFrame], cascade: Cascade) -> list[Signal]:
    liq = pack["liq"].copy()
    prev_hi = liq["mid_high"].rolling(20).max().shift(1)
    prev_lo = liq["mid_low"].rolling(20).min().shift(1)
    atr = liq["atr14"]
    bull = (liq["mid_low"] < prev_lo - atr * 0.05) & (liq["mid_close"] > prev_lo)
    bear = (liq["mid_high"] > prev_hi + atr * 0.05) & (liq["mid_close"] < prev_hi)

    events = []
    for i in np.flatnonzero((bull | bear).fillna(False).to_numpy()):
        r = liq.iloc[i]
        if bull.iloc[i]:
            events.append((r.time, 1, float(prev_lo.iloc[i]), float(r.mid_low)))
        else:
            events.append((r.time, -1, float(prev_hi.iloc[i]), float(r.mid_high)))

    e = pack["entry"].copy()
    out: list[Signal] = []
    times = e["time"].to_numpy()
    for t, direction, level, extreme in events:
        start = int(np.searchsorted(times, np.datetime64(t.to_datetime64()), side="right"))
        stop_i = min(len(e), start + 12)
        for j in range(start, stop_i):
            r = e.iloc[j]
            atrj = float(r.atr14) if np.isfinite(r.atr14) else 0.0
            if atrj <= 0:
                continue
            if direction == 1:
                mss = r.mid_close > r.prior_high5
                disp = r.mid_close > r.mid_open and r.body >= atrj * 0.70 and r.body_eff >= 0.55
                if mss and disp:
                    out.append(Signal("QEDGE_01_LIQUIDITY_REVERSAL", cascade.name, 1, r.time, level, extreme, "sweep-low/reclaim+mss"))
                    break
            else:
                mss = r.mid_close < r.prior_low5
                disp = r.mid_close < r.mid_open and r.body >= atrj * 0.70 and r.body_eff >= 0.55
                if mss and disp:
                    out.append(Signal("QEDGE_01_LIQUIDITY_REVERSAL", cascade.name, -1, r.time, level, extreme, "sweep-high/reclaim+mss"))
                    break
    return out


def trend_pullback(pack: dict[str, pd.DataFrame], cascade: Cascade) -> list[Signal]:
    e = pack["entry"].copy()
    trend = pack["trend"]
    liq = pack["liq"]
    e = merge_context(e, trend, "t_", ["mid_close", "ema20", "ema50", "ema50_slope3_atr", "efficiency20"])
    e = merge_context(e, liq, "l_", ["mid_close", "mid_low", "mid_high", "ema9", "ema21", "atr14"])

    out: list[Signal] = []
    for i in range(20, len(e) - 1):
        r = e.iloc[i]
        td = trend_direction(r, "t_")
        if td == 0 or not np.isfinite(r.atr14):
            continue
        if td == 1:
            pullback = r.l_mid_low <= max(r.l_ema9, r.l_ema21) and r.l_mid_close >= min(r.l_ema9, r.l_ema21)
            trigger = r.mid_close > r.prior_high5 and r.mid_close > r.mid_open
            if pullback and trigger:
                stop_ref = float(e.iloc[max(0, i - 5): i + 1]["mid_low"].min())
                out.append(Signal("QEDGE_02_TREND_PULLBACK", cascade.name, 1, r.time, float(r.mid_close), stop_ref, "trend-up+pullback+break"))
        else:
            pullback = r.l_mid_high >= min(r.l_ema9, r.l_ema21) and r.l_mid_close <= max(r.l_ema9, r.l_ema21)
            trigger = r.mid_close < r.prior_low5 and r.mid_close < r.mid_open
            if pullback and trigger:
                stop_ref = float(e.iloc[max(0, i - 5): i + 1]["mid_high"].max())
                out.append(Signal("QEDGE_02_TREND_PULLBACK", cascade.name, -1, r.time, float(r.mid_close), stop_ref, "trend-down+pullback+break"))
    return out


def breakout_retest(pack: dict[str, pd.DataFrame], cascade: Cascade) -> list[Signal]:
    liq = pack["liq"].copy()
    bull_break = (
        (liq["mid_close"] > liq["prior_high20"] + liq["atr14"] * 0.10)
        & (liq["mid_close"] > liq["mid_open"])
        & (liq["body_eff"] >= 0.60)
    )
    bear_break = (
        (liq["mid_close"] < liq["prior_low20"] - liq["atr14"] * 0.10)
        & (liq["mid_close"] < liq["mid_open"])
        & (liq["body_eff"] >= 0.60)
    )
    events = []
    for i in np.flatnonzero((bull_break | bear_break).fillna(False).to_numpy()):
        r = liq.iloc[i]
        if bull_break.iloc[i]:
            events.append((r.time, 1, float(r.prior_high20)))
        else:
            events.append((r.time, -1, float(r.prior_low20)))

    e = pack["entry"]
    out: list[Signal] = []
    times = e["time"].to_numpy()
    for t, direction, level in events:
        start = int(np.searchsorted(times, np.datetime64(t.to_datetime64()), side="right"))
        stop_i = min(len(e), start + 10)
        for j in range(start, stop_i):
            r = e.iloc[j]
            if not np.isfinite(r.atr14):
                continue
            tol = float(r.atr14) * 0.15
            if direction == 1:
                retest = r.mid_low <= level + tol and r.mid_close > level and r.mid_close > r.mid_open
                if retest:
                    out.append(Signal("QEDGE_03_BREAKOUT_RETEST", cascade.name, 1, r.time, level, float(r.mid_low), "range-break+retest"))
                    break
            else:
                retest = r.mid_high >= level - tol and r.mid_close < level and r.mid_close < r.mid_open
                if retest:
                    out.append(Signal("QEDGE_03_BREAKOUT_RETEST", cascade.name, -1, r.time, level, float(r.mid_high), "range-break+retest"))
                    break
    return out


def session_levels(m1: pd.DataFrame) -> pd.DataFrame:
    x = m1.copy()
    x["date"] = x["time"].dt.floor("D")
    x["hour"] = x["time"].dt.hour
    asian = x[(x["hour"] >= 0) & (x["hour"] < 7)].groupby("date").agg(
        asian_high=("mid_high", "max"), asian_low=("mid_low", "min")
    )
    london = x[(x["hour"] >= 7) & (x["hour"] < 13)].groupby("date").agg(
        london_high=("mid_high", "max"), london_low=("mid_low", "min")
    )
    return asian.join(london, how="outer").reset_index()


def london_raid(pack: dict[str, pd.DataFrame], cascade: Cascade, levels: pd.DataFrame) -> list[Signal]:
    e = pack["entry"].copy()
    e["date"] = e["time"].dt.floor("D")
    e = e.merge(levels[["date", "asian_high", "asian_low"]], on="date", how="left")
    h = e["time"].dt.hour
    active = (h >= 7) & (h < 12)
    out: list[Signal] = []
    for i in np.flatnonzero(active.fillna(False).to_numpy()):
        r = e.iloc[i]
        if not np.isfinite(r.asian_high) or not np.isfinite(r.asian_low) or not np.isfinite(r.atr14):
            continue
        if r.mid_low < r.asian_low - r.atr14 * 0.05 and r.mid_close > r.asian_low:
            out.append(Signal("QEDGE_04_LONDON_RAID", cascade.name, 1, r.time, float(r.asian_low), float(r.mid_low), "asian-low raid/reclaim"))
        elif r.mid_high > r.asian_high + r.atr14 * 0.05 and r.mid_close < r.asian_high:
            out.append(Signal("QEDGE_04_LONDON_RAID", cascade.name, -1, r.time, float(r.asian_high), float(r.mid_high), "asian-high raid/reclaim"))
    return out


def ny_continuation_reversal(pack: dict[str, pd.DataFrame], cascade: Cascade, levels: pd.DataFrame) -> list[Signal]:
    e = pack["entry"].copy()
    trend = pack["trend"]
    e = merge_context(e, trend, "t_", ["mid_close", "ema20", "ema50", "ema50_slope3_atr", "efficiency20"])
    e["date"] = e["time"].dt.floor("D")
    e = e.merge(levels[["date", "london_high", "london_low"]], on="date", how="left")
    h = e["time"].dt.hour
    active = (h >= 13) & (h < 17)
    out: list[Signal] = []

    for i in np.flatnonzero(active.fillna(False).to_numpy()):
        r = e.iloc[i]
        if not np.isfinite(r.london_high) or not np.isfinite(r.london_low) or not np.isfinite(r.atr14):
            continue
        td = trend_direction(r, "t_")
        tol = float(r.atr14) * 0.10

        # Trend-compatible continuation through the London range.
        if td == 1 and r.mid_low <= r.london_high + tol and r.mid_close > r.london_high and r.mid_close > r.mid_open:
            out.append(Signal("QEDGE_05_NY_CONT_REV", cascade.name, 1, r.time, float(r.london_high), float(r.mid_low), "NY continuation above London high"))
            continue
        if td == -1 and r.mid_high >= r.london_low - tol and r.mid_close < r.london_low and r.mid_close < r.mid_open:
            out.append(Signal("QEDGE_05_NY_CONT_REV", cascade.name, -1, r.time, float(r.london_low), float(r.mid_high), "NY continuation below London low"))
            continue

        # Counter-move reversal only after a clear raid/reclaim.
        if r.mid_high > r.london_high + tol and r.mid_close < r.london_high:
            out.append(Signal("QEDGE_05_NY_CONT_REV", cascade.name, -1, r.time, float(r.london_high), float(r.mid_high), "NY London-high raid/reversal"))
        elif r.mid_low < r.london_low - tol and r.mid_close > r.london_low:
            out.append(Signal("QEDGE_05_NY_CONT_REV", cascade.name, 1, r.time, float(r.london_low), float(r.mid_low), "NY London-low raid/reversal"))
    return out


def dedupe_signals(signals: list[Signal], entry_rule: str) -> list[Signal]:
    if not signals:
        return []
    # At most one signal of a strategy/direction per entry bar.
    seen = set()
    out = []
    for s in sorted(signals, key=lambda z: z.signal_time):
        key = (s.strategy, s.cascade, s.direction, s.signal_time.floor(entry_rule))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def simulate(
    entry_bars: pd.DataFrame,
    signals: list[Signal],
    *,
    reward_risk: float = 2.0,
    stop_buffer_atr: float = 0.10,
    max_hold_bars: int = 96,
) -> list[Trade]:
    if not signals:
        return []
    e = entry_bars.reset_index(drop=True)
    times = e["time"].to_numpy()
    trades: list[Trade] = []
    next_available = 0

    for s in sorted(signals, key=lambda z: z.signal_time):
        sig_i = int(np.searchsorted(times, np.datetime64(s.signal_time.to_datetime64()), side="left"))
        entry_i = sig_i + 1
        if entry_i <= next_available or entry_i >= len(e):
            continue
        row = e.iloc[entry_i]
        atr = float(row.atr14) if np.isfinite(row.atr14) else 0.0
        if atr <= 0:
            continue

        if s.direction == 1:
            entry = float(row.ask_open)
            stop = float(min(s.stop_ref, entry - atr * 0.25) - atr * stop_buffer_atr)
            risk = entry - stop
            if risk <= 0 or risk > atr * 5:
                continue
            target = entry + reward_risk * risk
        else:
            entry = float(row.bid_open)
            stop = float(max(s.stop_ref, entry + atr * 0.25) + atr * stop_buffer_atr)
            risk = stop - entry
            if risk <= 0 or risk > atr * 5:
                continue
            target = entry - reward_risk * risk

        mfe = 0.0
        mae = 0.0
        exit_price = entry
        exit_time = row.time
        reason = "TIME"
        end_i = min(len(e) - 1, entry_i + max_hold_bars)

        for j in range(entry_i, end_i + 1):
            b = e.iloc[j]
            if s.direction == 1:
                adverse = float(b.bid_low)
                favorable = float(b.bid_high)
                mae = max(mae, max(0.0, (entry - adverse) / risk))
                mfe = max(mfe, max(0.0, (favorable - entry) / risk))
                sl_hit = adverse <= stop
                tp_hit = favorable >= target
                if sl_hit or tp_hit:
                    exit_price = stop if sl_hit else target
                    reason = "SL" if sl_hit else "TP"
                    exit_time = b.time
                    end_i = j
                    break
                exit_price = float(b.bid_close)
                exit_time = b.time
            else:
                adverse = float(b.ask_high)
                favorable = float(b.ask_low)
                mae = max(mae, max(0.0, (adverse - entry) / risk))
                mfe = max(mfe, max(0.0, (entry - favorable) / risk))
                sl_hit = adverse >= stop
                tp_hit = favorable <= target
                if sl_hit or tp_hit:
                    exit_price = stop if sl_hit else target
                    reason = "SL" if sl_hit else "TP"
                    exit_time = b.time
                    end_i = j
                    break
                exit_price = float(b.ask_close)
                exit_time = b.time

        r_mult = ((exit_price - entry) / risk) * s.direction
        trades.append(Trade(
            strategy=s.strategy,
            cascade=s.cascade,
            direction=s.direction,
            signal_time=s.signal_time,
            entry_time=row.time,
            exit_time=exit_time,
            entry=entry,
            stop=stop,
            target=target,
            exit=exit_price,
            initial_risk=risk,
            r=float(r_mult),
            mfe_r=float(mfe),
            mae_r=float(mae),
            bars=int(end_i - entry_i + 1),
            reason=reason,
            note=s.note,
        ))
        next_available = end_i

    return trades


def max_drawdown_r(rs: np.ndarray) -> float:
    if len(rs) == 0:
        return 0.0
    eq = np.r_[0.0, np.cumsum(rs)]
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq))


def metrics(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "campaigns": 0, "win_rate": 0.0, "expectancy_r": 0.0, "pf_r": 0.0,
            "net_r": 0.0, "max_dd_r": 0.0, "median_r": 0.0,
            "avg_mfe_r": 0.0, "avg_mae_r": 0.0, "long_campaigns": 0,
            "short_campaigns": 0, "long_net_r": 0.0, "short_net_r": 0.0,
        }
    rs = np.array([t.r for t in trades], dtype=float)
    wins = rs[rs > 0].sum()
    losses = -rs[rs < 0].sum()
    longs = [t for t in trades if t.direction == 1]
    shorts = [t for t in trades if t.direction == -1]
    return {
        "campaigns": int(len(trades)),
        "win_rate": float((rs > 0).mean()),
        "expectancy_r": float(rs.mean()),
        "pf_r": float(wins / losses) if losses > 0 else (999.0 if wins > 0 else 0.0),
        "net_r": float(rs.sum()),
        "max_dd_r": max_drawdown_r(rs),
        "median_r": float(np.median(rs)),
        "avg_mfe_r": float(np.mean([t.mfe_r for t in trades])),
        "avg_mae_r": float(np.mean([t.mae_r for t in trades])),
        "long_campaigns": len(longs),
        "short_campaigns": len(shorts),
        "long_net_r": float(sum(t.r for t in longs)),
        "short_net_r": float(sum(t.r for t in shorts)),
    }


def evidence_score(m: dict) -> float:
    n = int(m["campaigns"])
    if n <= 0:
        return -1e9
    reliability = n / (n + 40.0)
    pf = min(max(float(m["pf_r"]), 0.0), 4.0)
    shrunk_pf = 1.0 + (pf - 1.0) * reliability
    shrunk_exp = float(m["expectancy_r"]) * reliability
    sample = min(1.0, n / 60.0)
    score = 2.0 * sample + 2.0 * (shrunk_pf - 1.0) + math.tanh(shrunk_exp * 3.0) - float(m["max_dd_r"]) / 20.0
    if n < 30:
        score -= 2.0 * (30 - n) / 30.0
    return float(score)


def subset(trades: list[Trade], start: pd.Timestamp | None, end: pd.Timestamp | None) -> list[Trade]:
    out = []
    for t in trades:
        if start is not None and t.entry_time < start:
            continue
        if end is not None and t.entry_time >= end:
            continue
        out.append(t)
    return out


def bootstrap_mean_ci(trades: list[Trade], sims: int = 3000, seed: int = 260924) -> dict:
    rs = np.array([t.r for t in trades], dtype=float)
    if len(rs) < 2:
        return {"n": int(len(rs)), "mean_r": float(rs.mean()) if len(rs) else 0.0, "p05": 0.0, "p50": 0.0, "p95": 0.0, "prob_mean_le_zero": 1.0}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rs), size=(sims, len(rs)))
    means = rs[idx].mean(axis=1)
    return {
        "n": int(len(rs)),
        "mean_r": float(rs.mean()),
        "p05": float(np.quantile(means, 0.05)),
        "p50": float(np.quantile(means, 0.50)),
        "p95": float(np.quantile(means, 0.95)),
        "prob_mean_le_zero": float((means <= 0).mean()),
    }


def yearly_breakdown(trades: list[Trade]) -> list[dict]:
    by: dict[int, list[Trade]] = {}
    for t in trades:
        by.setdefault(int(t.entry_time.year), []).append(t)
    return [{"year": year, **metrics(rows)} for year, rows in sorted(by.items())]


def daily_series(trades: list[Trade]) -> pd.Series:
    if not trades:
        return pd.Series(dtype=float)
    s = pd.Series(
        [t.r for t in trades],
        index=pd.DatetimeIndex([t.exit_time.floor("D") for t in trades]),
        dtype=float,
    )
    return s.groupby(level=0).sum().sort_index()


def portfolio_summary(selected: list[tuple[str, str, list[Trade]]], holdout_start: pd.Timestamp) -> dict:
    series = {}
    for strategy, cascade, trades in selected:
        h = subset(trades, holdout_start, None)
        series[f"{strategy}__{cascade}"] = daily_series(h)
    if not series:
        return {"strategies": [], "correlation": {}, "holdout_equal_weight": {}}
    frame = pd.concat(series, axis=1).fillna(0.0)
    corr = frame.corr().round(4).fillna(0.0)
    # Equal-risk contribution per selected strategy: daily portfolio R is the
    # mean of strategy daily R, not the sum, so nominal risk does not multiply.
    port = frame.mean(axis=1) if len(frame.columns) else pd.Series(dtype=float)
    rs = port.to_numpy(dtype=float)
    portfolio = {
        "days": int(len(port)),
        "net_r": float(rs.sum()) if len(rs) else 0.0,
        "mean_daily_r": float(rs.mean()) if len(rs) else 0.0,
        "positive_day_fraction": float((rs > 0).mean()) if len(rs) else 0.0,
        "max_dd_r": max_drawdown_r(rs),
    }
    return {
        "strategies": list(series),
        "correlation": corr.to_dict(),
        "holdout_equal_weight": portfolio,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="research_data")
    ap.add_argument("--out", default="qedge_portfolio_results")
    ap.add_argument("--start", default="2021-08-20")
    ap.add_argument("--end", default="2026-08-20")
    ap.add_argument("--holdout-start", default="2026-04-20")
    ap.add_argument("--reward-risk", type=float, default=2.0)
    ap.add_argument("--max-hold-bars", type=int, default=96)
    args = ap.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    m1 = load_m1(root)
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(days=1)
    holdout = pd.Timestamp(args.holdout_start, tz="UTC")
    m1 = m1[(m1["time"] >= start) & (m1["time"] < end)].reset_index(drop=True)

    # Mid prices are needed for session-level construction before per-cascade resampling.
    m1 = resample_bars(m1, "1min")
    levels = session_levels(m1)

    all_trades: list[Trade] = []
    variant_rows = []
    trade_map: dict[tuple[str, str], list[Trade]] = {}

    for cascade in CASCADES:
        print(f"BUILD {cascade.name}", flush=True)
        pack = build_pack(m1, cascade)
        strategy_signals = [
            liquidity_reversal(pack, cascade),
            trend_pullback(pack, cascade),
            breakout_retest(pack, cascade),
            london_raid(pack, cascade, levels),
            ny_continuation_reversal(pack, cascade, levels),
        ]
        for signals in strategy_signals:
            signals = dedupe_signals(signals, cascade.entry)
            strategy = signals[0].strategy if signals else "UNKNOWN"
            # If a strategy emitted zero signals, recover its name by position.
            if strategy == "UNKNOWN":
                strategy = [
                    "QEDGE_01_LIQUIDITY_REVERSAL",
                    "QEDGE_02_TREND_PULLBACK",
                    "QEDGE_03_BREAKOUT_RETEST",
                    "QEDGE_04_LONDON_RAID",
                    "QEDGE_05_NY_CONT_REV",
                ][strategy_signals.index(signals)]
            trades = simulate(
                pack["entry"],
                signals,
                reward_risk=args.reward_risk,
                max_hold_bars=args.max_hold_bars,
            )
            trade_map[(strategy, cascade.name)] = trades
            all_trades.extend(trades)
            dev = subset(trades, None, holdout)
            ho = subset(trades, holdout, None)
            dm = metrics(dev)
            hm = metrics(ho)
            variant_rows.append({
                "strategy": strategy,
                "cascade": cascade.name,
                "entry_tf": cascade.entry,
                "liquidity_tf": cascade.liquidity,
                "trend_tf": cascade.trend,
                "context_tf": cascade.context,
                "development": dm,
                "holdout": hm,
                "development_score": evidence_score(dm),
                "yearly": yearly_breakdown(trades),
            })
            print(strategy, cascade.name, "DEV", dm["campaigns"], round(dm["expectancy_r"], 4), round(dm["pf_r"], 3),
                  "HOLD", hm["campaigns"], round(hm["expectancy_r"], 4), round(hm["pf_r"], 3), flush=True)

    # Select exactly one cascade per independent strategy using development
    # evidence only. Holdout metrics are never part of selection.
    selected = []
    selection = []
    for strategy in sorted({r["strategy"] for r in variant_rows if r["strategy"] != "UNKNOWN"}):
        candidates = [r for r in variant_rows if r["strategy"] == strategy]
        eligible = [r for r in candidates if r["development"]["campaigns"] >= 30 and r["development"]["expectancy_r"] > 0 and r["development"]["pf_r"] > 1.0]
        ranked = sorted(eligible if eligible else candidates, key=lambda r: r["development_score"], reverse=True)
        best = ranked[0]
        key = (strategy, best["cascade"])
        trades = trade_map[key]
        ho = subset(trades, holdout, None)
        boot = bootstrap_mean_ci(ho)
        selection.append({
            "strategy": strategy,
            "selected_cascade": best["cascade"],
            "selected_on": "development_only",
            "development": best["development"],
            "development_score": best["development_score"],
            "holdout": best["holdout"],
            "holdout_bootstrap_mean_r": boot,
            "yearly": best["yearly"],
            "status": (
                "HOLDOUT_SUPPORT"
                if best["holdout"]["campaigns"] >= 20
                and best["holdout"]["expectancy_r"] > 0
                and best["holdout"]["pf_r"] > 1.05
                and boot["p05"] > 0
                else "RESEARCH"
            ),
        })
        selected.append((strategy, best["cascade"], trades))

    portfolio = portfolio_summary(selected, holdout)

    trades_df = pd.DataFrame([asdict(t) for t in all_trades])
    if not trades_df.empty:
        trades_df.to_parquet(out / "trades.parquet", index=False)
        trades_df.to_csv(out / "trades.csv", index=False)

    payload = {
        "methodology": {
            "data": "pinned external XAUUSD M1 bid/ask OHLC",
            "start": str(start),
            "end_exclusive": str(end),
            "development": f"{start} -> {holdout}",
            "holdout": f"{holdout} -> {end}",
            "holdout_note": "Historical validation holdout, not future-unseen data. Forward demo remains required.",
            "selection_unit": "independent campaign",
            "performance_unit": "R multiple",
            "signal_authority": "closed bars only",
            "entry": "next execution bar open",
            "same_bar_sl_tp": "SL wins",
            "reward_risk": args.reward_risk,
            "max_hold_bars": args.max_hold_bars,
            "strategies": [
                "QEDGE_01_LIQUIDITY_REVERSAL",
                "QEDGE_02_TREND_PULLBACK",
                "QEDGE_03_BREAKOUT_RETEST",
                "QEDGE_04_LONDON_RAID",
                "QEDGE_05_NY_CONT_REV",
            ],
            "cascades": [asdict(c) for c in CASCADES],
            "broker_native_confirmation_required": True,
            "live_trading": False,
        },
        "variants": variant_rows,
        "selection": selection,
        "portfolio": portfolio,
    }
    (out / "report.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        "# ASTRA QEDGE 5Y Multi-Strategy Research",
        "",
        "Development selection uses only pre-holdout data. The historical holdout is reported afterward and is not future-unseen evidence.",
        "",
        "| Strategy | Selected cascade | Dev campaigns | Dev PF(R) | Dev exp(R) | Holdout campaigns | Holdout PF(R) | Holdout exp(R) | Bootstrap p05 mean R | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for s in selection:
        d = s["development"]
        h = s["holdout"]
        b = s["holdout_bootstrap_mean_r"]
        lines.append(
            f"| {s['strategy']} | {s['selected_cascade']} | {d['campaigns']} | {d['pf_r']:.2f} | {d['expectancy_r']:.3f} | "
            f"{h['campaigns']} | {h['pf_r']:.2f} | {h['expectancy_r']:.3f} | {b['p05']:.3f} | {s['status']} |"
        )
    lines += [
        "",
        "## Equal-risk holdout portfolio",
        "",
        f"- Strategies: {len(portfolio.get('strategies', []))}",
        f"- Net R: {portfolio.get('holdout_equal_weight', {}).get('net_r', 0.0):.3f}",
        f"- Mean daily R: {portfolio.get('holdout_equal_weight', {}).get('mean_daily_r', 0.0):.4f}",
        f"- Max DD R: {portfolio.get('holdout_equal_weight', {}).get('max_dd_r', 0.0):.3f}",
        "",
        "No result in this report authorizes live trading. Native MT5/broker confirmation and forward demo evidence remain mandatory.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
