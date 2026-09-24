from __future__ import annotations

"""ASTRA Market Brain V8 — deterministic market-state model.

This module consolidates the market knowledge accumulated by AUREON/ASTRA into
an explicit state vector. It does not forecast prices and it does not authorize
execution. Every field is derived from information available at or before the
completed bar being labelled.

The Market Brain answers:
- What regime is active?
- What is structure doing?
- What liquidity event just occurred?
- Where is price within its recent range?
- Is volatility compressing or expanding?
- Is momentum directional or neutral?
- Is there displacement / an FVG?
- Which QEDGE family is structurally compatible with this state?
- What event is still required before a strategy could trigger?

Volume Profile, CVD, GEX and order-flow fields remain explicitly unavailable
unless a future data adapter supplies data with the required authority.
"""

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BRAIN_COLUMNS = [
    "time",
    "regime",
    "structure",
    "liquidity_state",
    "session",
    "location",
    "volatility",
    "momentum",
    "displacement",
    "fvg_state",
    "trend_bias",
    "context_bias",
    "contradictions",
    "route_qedge_01",
    "route_qedge_02",
    "route_qedge_03",
    "route_qedge_04",
    "route_qedge_05",
    "router_choice",
    "router_score",
    "next_required_event",
    "volume_authority",
    "orderflow_authority",
    "gex_authority",
]


def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except Exception:
        return False


def _merge_context(base: pd.DataFrame, higher: pd.DataFrame, prefix: str, columns: Iterable[str]) -> pd.DataFrame:
    rhs = higher[["time", *columns]].copy()
    rhs = rhs.rename(columns={c: f"{prefix}{c}" for c in columns})
    return pd.merge_asof(
        base.sort_values("time"),
        rhs.sort_values("time"),
        on="time",
        direction="backward",
        allow_exact_matches=True,
    )


def _direction(close, ema20, ema50, slope, efficiency) -> int:
    vals = [close, ema20, ema50, slope, efficiency]
    if not all(_finite(v) for v in vals):
        return 0
    close, ema20, ema50, slope, efficiency = map(float, vals)
    if close > ema20 > ema50 and slope > 0.01 and efficiency >= 0.18:
        return 1
    if close < ema20 < ema50 and slope < -0.01 and efficiency >= 0.18:
        return -1
    return 0


def _regime(row: pd.Series) -> str:
    atrp = row.get("atr_pct")
    gap = row.get("ema_gap_atr")
    slope = row.get("ema50_slope3_atr")
    eff = row.get("efficiency20")
    rng = row.get("range20_atr")
    if not all(_finite(v) for v in (atrp, gap, slope, eff, rng)):
        return "WARMUP"
    atrp, gap, slope, eff, rng = map(float, (atrp, gap, slope, eff, rng))
    if atrp <= 0.20 and rng <= 7.0:
        return "COMPRESSION"
    if atrp >= 0.85:
        if gap >= 0.25 and slope > 0:
            return "EXPANSION_UP"
        if gap <= -0.25 and slope < 0:
            return "EXPANSION_DOWN"
        return "HIGH_VOL_TRANSITION"
    if gap >= 0.35 and slope > 0.015 and eff >= 0.22:
        return "TREND_UP"
    if gap <= -0.35 and slope < -0.015 and eff >= 0.22:
        return "TREND_DOWN"
    if abs(gap) <= 0.25 and eff <= 0.28:
        return "RANGE"
    return "TRANSITION"


def _session(ts: pd.Timestamp) -> str:
    h = int(ts.hour)
    if 0 <= h < 7:
        return "ASIA"
    if 7 <= h < 13:
        return "LONDON"
    if 13 <= h < 17:
        return "NEW_YORK"
    if 17 <= h < 21:
        return "LATE_NEW_YORK"
    return "OFF_HOURS"


def _router(row: pd.Series) -> tuple[int, int, int, int, int, str, int, str]:
    regime = str(row["regime"])
    liq = str(row["liquidity_state"])
    session = str(row["session"])
    location = str(row["location"])
    displacement = str(row["displacement"])
    structure = str(row["structure"])
    fvg = str(row["fvg_state"])
    trend_bias = int(row["trend_bias"])
    context_bias = int(row["context_bias"])

    q1 = 0  # liquidity reversal
    if liq in ("SELL_SIDE_SWEPT", "BUY_SIDE_SWEPT"):
        q1 += 3
    if regime in ("RANGE", "TRANSITION", "HIGH_VOL_TRANSITION"):
        q1 += 1
    if displacement != "NONE":
        q1 += 1
    if fvg != "NONE":
        q1 += 1

    q2 = 0  # trend pullback
    if regime in ("TREND_UP", "TREND_DOWN", "EXPANSION_UP", "EXPANSION_DOWN"):
        q2 += 2
    if trend_bias != 0:
        q2 += 2
    if context_bias == trend_bias and trend_bias != 0:
        q2 += 1
    if (trend_bias == 1 and location != "PREMIUM") or (trend_bias == -1 and location != "DISCOUNT"):
        q2 += 1

    q3 = 0  # breakout retest
    if liq in ("BREAKOUT_UP", "BREAKOUT_DOWN"):
        q3 += 3
    if displacement != "NONE":
        q3 += 1
    if regime in ("COMPRESSION", "EXPANSION_UP", "EXPANSION_DOWN", "TRANSITION"):
        q3 += 1
    if fvg != "NONE":
        q3 += 1

    q4 = 0  # London raid
    if session == "LONDON":
        q4 += 3
    if liq in ("SELL_SIDE_SWEPT", "BUY_SIDE_SWEPT"):
        q4 += 3
    if structure in ("MIXED", "HH_HL", "LH_LL"):
        q4 += 1

    q5 = 0  # New York continuation/reversal
    if session == "NEW_YORK":
        q5 += 3
    if liq in ("SELL_SIDE_SWEPT", "BUY_SIDE_SWEPT", "BREAKOUT_UP", "BREAKOUT_DOWN"):
        q5 += 2
    if trend_bias != 0 or regime in ("TREND_UP", "TREND_DOWN", "EXPANSION_UP", "EXPANSION_DOWN"):
        q5 += 1

    scores = {
        "QEDGE_01_LIQUIDITY_REVERSAL": q1,
        "QEDGE_02_TREND_PULLBACK": q2,
        "QEDGE_03_BREAKOUT_RETEST": q3,
        "QEDGE_04_LONDON_RAID": q4,
        "QEDGE_05_NY_CONT_REV": q5,
    }
    choice, score = max(scores.items(), key=lambda kv: kv[1])
    if score < 4:
        choice = "WAIT"

    if regime == "WARMUP":
        next_event = "WAIT_FOR_SUFFICIENT_HISTORY"
    elif liq in ("SELL_SIDE_SWEPT", "BUY_SIDE_SWEPT") and displacement == "NONE":
        next_event = "WAIT_FOR_MSS_OR_DISPLACEMENT"
    elif regime == "COMPRESSION" and liq not in ("BREAKOUT_UP", "BREAKOUT_DOWN"):
        next_event = "WAIT_FOR_RANGE_EXPANSION"
    elif choice == "QEDGE_02_TREND_PULLBACK" and location in ("PREMIUM", "DISCOUNT"):
        aligned_extreme = (trend_bias == 1 and location == "PREMIUM") or (trend_bias == -1 and location == "DISCOUNT")
        next_event = "WAIT_FOR_PULLBACK" if aligned_extreme else "WAIT_FOR_EXECUTION_TRIGGER"
    elif liq in ("BREAKOUT_UP", "BREAKOUT_DOWN") and choice == "QEDGE_03_BREAKOUT_RETEST":
        next_event = "WAIT_FOR_RETEST_CONFIRMATION"
    elif choice == "WAIT":
        next_event = "WAIT_FOR_STRATEGY_COMPATIBLE_STATE"
    else:
        next_event = "WAIT_FOR_EXECUTION_TRIGGER"

    return q1, q2, q3, q4, q5, choice, int(score), next_event


def prepare_entry_features(entry: pd.DataFrame) -> pd.DataFrame:
    """Add only causal features needed by the market-state classifier."""
    x = entry.copy()

    if "atr14" not in x:
        prev = x["mid_close"].shift(1)
        tr = pd.concat([
            (x["mid_high"] - x["mid_low"]).abs(),
            (x["mid_high"] - prev).abs(),
            (x["mid_low"] - prev).abs(),
        ], axis=1).max(axis=1)
        x["atr14"] = tr.ewm(alpha=1 / 14.0, adjust=False, min_periods=14).mean()

    for p in (20, 50):
        key = f"ema{p}"
        if key not in x:
            x[key] = x["mid_close"].ewm(span=p, adjust=False, min_periods=p).mean()

    if "body" not in x:
        x["body"] = (x["mid_close"] - x["mid_open"]).abs()
    if "range" not in x:
        x["range"] = (x["mid_high"] - x["mid_low"]).abs()
    if "body_eff" not in x:
        x["body_eff"] = x["body"] / x["range"].replace(0, np.nan)
    if "ema50_slope3_atr" not in x:
        x["ema50_slope3_atr"] = (x["ema50"] - x["ema50"].shift(3)) / (3 * x["atr14"].replace(0, np.nan))
    if "efficiency20" not in x:
        movement = x["mid_close"].diff().abs().rolling(20).sum()
        x["efficiency20"] = (x["mid_close"] - x["mid_close"].shift(20)).abs() / movement.replace(0, np.nan)

    x["ema_gap_atr"] = (x["ema20"] - x["ema50"]) / x["atr14"].replace(0, np.nan)
    x["atr_pct"] = x["atr14"].rolling(252, min_periods=80).rank(pct=True)
    x["range20_atr"] = (
        x["mid_high"].rolling(20).max() - x["mid_low"].rolling(20).min()
    ) / x["atr14"].replace(0, np.nan)

    x["prior_high20_brain"] = x["mid_high"].rolling(20).max().shift(1)
    x["prior_low20_brain"] = x["mid_low"].rolling(20).min().shift(1)
    x["range50_high"] = x["mid_high"].rolling(50).max()
    x["range50_low"] = x["mid_low"].rolling(50).min()

    older_high = x["mid_high"].shift(10).rolling(10).max()
    older_low = x["mid_low"].shift(10).rolling(10).min()
    newer_high = x["mid_high"].rolling(10).max()
    newer_low = x["mid_low"].rolling(10).min()
    x["structure"] = np.select(
        [
            (newer_high > older_high) & (newer_low > older_low),
            (newer_high < older_high) & (newer_low < older_low),
        ],
        ["HH_HL", "LH_LL"],
        default="MIXED",
    )

    x["liquidity_state"] = np.select(
        [
            (x["mid_low"] < x["prior_low20_brain"]) & (x["mid_close"] > x["prior_low20_brain"]),
            (x["mid_high"] > x["prior_high20_brain"]) & (x["mid_close"] < x["prior_high20_brain"]),
            x["mid_close"] > x["prior_high20_brain"],
            x["mid_close"] < x["prior_low20_brain"],
        ],
        ["SELL_SIDE_SWEPT", "BUY_SIDE_SWEPT", "BREAKOUT_UP", "BREAKOUT_DOWN"],
        default="INSIDE_RANGE",
    )

    width = (x["range50_high"] - x["range50_low"]).replace(0, np.nan)
    loc = (x["mid_close"] - x["range50_low"]) / width
    x["location"] = np.select(
        [loc <= 0.35, loc >= 0.65],
        ["DISCOUNT", "PREMIUM"],
        default="EQUILIBRIUM",
    )

    x["volatility"] = np.select(
        [x["atr_pct"] <= 0.20, x["atr_pct"] >= 0.80],
        ["LOW", "HIGH"],
        default="NORMAL",
    )

    bullish_momentum = (
        (x["mid_close"] > x["mid_open"])
        & (x["body_eff"] >= 0.55)
        & (x["ema50_slope3_atr"] > 0)
    )
    bearish_momentum = (
        (x["mid_close"] < x["mid_open"])
        & (x["body_eff"] >= 0.55)
        & (x["ema50_slope3_atr"] < 0)
    )
    x["momentum"] = np.select(
        [bullish_momentum, bearish_momentum],
        ["BULLISH", "BEARISH"],
        default="NEUTRAL",
    )

    bull_disp = (
        (x["mid_close"] > x["mid_open"])
        & (x["body"] >= x["atr14"] * 0.90)
        & (x["body_eff"] >= 0.60)
    )
    bear_disp = (
        (x["mid_close"] < x["mid_open"])
        & (x["body"] >= x["atr14"] * 0.90)
        & (x["body_eff"] >= 0.60)
    )
    x["displacement"] = np.select(
        [bull_disp, bear_disp],
        ["BULLISH", "BEARISH"],
        default="NONE",
    )

    gap_min = x["atr14"] * 0.05
    bull_fvg = (x["mid_low"] - x["mid_high"].shift(2)) >= gap_min
    bear_fvg = (x["mid_low"].shift(2) - x["mid_high"]) >= gap_min
    x["fvg_state"] = np.select(
        [bull_fvg, bear_fvg],
        ["BULLISH_FVG", "BEARISH_FVG"],
        default="NONE",
    )

    x["regime"] = x.apply(_regime, axis=1)
    x["session"] = x["time"].map(_session)
    return x


def build_market_brain(
    entry: pd.DataFrame,
    trend: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    x = prepare_entry_features(entry)

    needed = ["mid_close", "ema20", "ema50", "ema50_slope3_atr", "efficiency20"]
    x = _merge_context(x, trend, "trend_", needed)
    x = _merge_context(x, context, "context_", needed)

    x["trend_bias"] = [
        _direction(r.trend_mid_close, r.trend_ema20, r.trend_ema50, r.trend_ema50_slope3_atr, r.trend_efficiency20)
        for r in x.itertuples(index=False)
    ]
    x["context_bias"] = [
        _direction(r.context_mid_close, r.context_ema20, r.context_ema50, r.context_ema50_slope3_atr, r.context_efficiency20)
        for r in x.itertuples(index=False)
    ]

    contradictions = []
    for r in x.itertuples(index=False):
        items = []
        if r.trend_bias != 0 and r.context_bias != 0 and r.trend_bias != r.context_bias:
            items.append("TREND_CONTEXT_CONFLICT")
        if r.structure == "HH_HL" and r.context_bias == -1:
            items.append("BULL_STRUCTURE_VS_BEAR_CONTEXT")
        if r.structure == "LH_LL" and r.context_bias == 1:
            items.append("BEAR_STRUCTURE_VS_BULL_CONTEXT")
        if r.displacement == "BULLISH" and r.momentum == "BEARISH":
            items.append("DISPLACEMENT_MOMENTUM_CONFLICT")
        if r.displacement == "BEARISH" and r.momentum == "BULLISH":
            items.append("DISPLACEMENT_MOMENTUM_CONFLICT")
        contradictions.append(";".join(items) if items else "NONE")
    x["contradictions"] = contradictions

    routed = x.apply(_router, axis=1, result_type="expand")
    routed.columns = [
        "route_qedge_01",
        "route_qedge_02",
        "route_qedge_03",
        "route_qedge_04",
        "route_qedge_05",
        "router_choice",
        "router_score",
        "next_required_event",
    ]
    x = pd.concat([x, routed], axis=1)

    # Explicit authority boundaries. These are not inferred from OHLC.
    x["volume_authority"] = "UNAVAILABLE_EXTERNAL_OHLC"
    x["orderflow_authority"] = "UNAVAILABLE_NO_AGGRESSOR_TRADE_DATA"
    x["gex_authority"] = "UNAVAILABLE_NO_OPTIONS_CHAIN"

    return x[BRAIN_COLUMNS].copy()


def state_at(brain: pd.DataFrame, ts: pd.Timestamp) -> dict:
    """Return the latest completed Market Brain state at or before ts."""
    if brain.empty:
        return {}
    times = brain["time"].astype("int64").to_numpy()
    idx = int(np.searchsorted(times, int(ts.value), side="right") - 1)
    if idx < 0:
        return {}
    row = brain.iloc[idx]
    out = {}
    for key in BRAIN_COLUMNS:
        value = row[key]
        if isinstance(value, np.generic):
            value = value.item()
        out[key] = value
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="research_data")
    ap.add_argument("--entry", default="5min")
    ap.add_argument("--liquidity", default="15min")
    ap.add_argument("--trend", default="1h")
    ap.add_argument("--context", default="4h")
    ap.add_argument("--out", default="market_brain_results")
    args = ap.parse_args()

    # Import at runtime to avoid a module cycle when qedge_portfolio imports
    # build_market_brain for campaign annotation.
    from qedge_portfolio import Cascade, build_pack, load_m1

    cascade = Cascade("CLI", args.entry, args.liquidity, args.trend, args.context)
    m1 = load_m1(Path(args.root))
    pack = build_pack(m1, cascade)
    brain = build_market_brain(pack["entry"], pack["trend"], pack["context"])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    brain.to_parquet(out / "market_state.parquet", index=False)

    last = state_at(brain, brain["time"].iloc[-1])
    counts = brain["router_choice"].value_counts().to_dict()
    payload = {
        "bars": int(len(brain)),
        "first": str(brain["time"].min()),
        "last": str(brain["time"].max()),
        "router_counts": {str(k): int(v) for k, v in counts.items()},
        "latest_state": last,
        "authority": {
            "forecast_probability": "NOT_PRODUCED",
            "execution": "BLOCKED",
            "volume_profile": "UNAVAILABLE_WITH_CURRENT_DATA",
            "cvd": "UNAVAILABLE_WITH_CURRENT_DATA",
            "gex": "UNAVAILABLE_WITH_CURRENT_DATA",
        },
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
