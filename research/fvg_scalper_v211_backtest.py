from __future__ import annotations

"""
Logic-level research harness for FVG_Scalper_V2_AutoLot.mq5 v2.11.

Purpose:
- Preserve the EA's FVG formation / persistence / retest / rejection logic.
- Use real bid/ask XAUUSD M1 OHLC from the pinned Dukascopy mirror.
- Separate signal edge (R-multiples) from aggressive money management.
- Run a small, pre-declared ablation matrix, then report in-sample and
  out-of-sample metrics.

This is NOT a tick-perfect MetaTrader reproduction. Intrabar retest/rejection
is approximated conservatively from M1 bid/ask OHLC. Promising variants must
be re-run in native MT5 before any forward-demo stage.
"""

import argparse
import json
import math
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Config:
    name: str
    min_fvg_atr: float = 0.15
    min_body_atr: float = 0.50
    min_body_ratio: float = 0.60
    max_fvg_bars: int = 1000
    replace_with_new_fvg: bool = True
    one_trade_per_fvg: bool = True
    use_bias: bool = False
    bias_tf: str = "1min"
    bias_fast: int = 20
    bias_slow: int = 50
    require_midpoint: bool = False
    require_rejection: bool = True
    reward_risk: float = 30.0
    max_sl_atr: float = 3.0
    atr_period: int = 14
    sl_atr_buffer: float = 0.15
    use_profit_lock: bool = True
    lock1_trigger_r: float = 0.50
    lock1_r: float = 0.10
    lock2_trigger_r: float = 1.00
    lock2_r: float = 0.35
    trail_start_r: float = 1.50
    trail_atr: float = 0.10
    max_spread_price: float = 0.80
    session_mode: str = "ALL"  # ALL or LONDON_NY_UTC
    one_position: bool = True


@dataclass
class Zone:
    bullish: bool
    low: float
    high: float
    formed_idx: int
    formed_time: pd.Timestamp
    traded: bool = False
    valid: bool = True


@dataclass
class Trade:
    direction: int
    entry_idx: int
    entry_time: pd.Timestamp
    entry: float
    sl0: float
    tp: float
    risk: float
    zone_low: float
    zone_high: float
    exit_idx: int = -1
    exit_time: Optional[pd.Timestamp] = None
    exit_price: float = np.nan
    exit_reason: str = ""
    r: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0
    bars: int = 0


def load_data(root: Path) -> pd.DataFrame:
    files = sorted((root / "XAUUSD" / "M1").glob("year=*/month=*/bars.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet bars under {root}/XAUUSD/M1")
    x = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    x = x.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    x["time"] = pd.to_datetime(x["time"], utc=True)

    # Mirror contains market-closed flat filler minutes. MT5 would receive no
    # ticks during these periods, so remove truly unchanged flat rows.
    prev_bid = x["bid_close"].shift(1)
    prev_ask = x["ask_close"].shift(1)
    active = (
        (x["bid_high"] > x["bid_low"]) |
        (x["ask_high"] > x["ask_low"]) |
        (x["bid_close"] != prev_bid) |
        (x["ask_close"] != prev_ask)
    )
    x = x.loc[active].reset_index(drop=True)

    # MT5 custom-symbol research uses bid OHLC for indicator calculations.
    h, l, c = x["bid_high"], x["bid_low"], x["bid_close"]
    prev = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14.0, adjust=False, min_periods=14).mean()
    x["spread_close"] = x["ask_close"] - x["bid_close"]
    return x


def bias_series(x: pd.DataFrame, tf: str, fast: int, slow: int) -> pd.Series:
    if tf == "1min":
        close = x.set_index("time")["bid_close"]
        f = close.ewm(span=fast, adjust=False, min_periods=fast).mean().shift(1)
        s = close.ewm(span=slow, adjust=False, min_periods=slow).mean().shift(1)
        sig = np.sign(f-s)
        return sig.reindex(x["time"]).set_axis(x.index)

    base = x.set_index("time")["bid_close"]
    # Label at right edge. Shift one completed HTF candle to prevent lookahead.
    close = base.resample(tf, label="right", closed="right").last().dropna()
    f = close.ewm(span=fast, adjust=False, min_periods=fast).mean().shift(1)
    s = close.ewm(span=slow, adjust=False, min_periods=slow).mean().shift(1)
    sig = np.sign(f-s).rename("bias").reset_index()
    mapped = pd.merge_asof(
        x[["time"]].reset_index(),
        sig.sort_values("time"),
        on="time",
        direction="backward",
    ).set_index("index")["bias"]
    return mapped.reindex(x.index)


def session_allowed(ts: pd.Timestamp, mode: str) -> bool:
    if mode == "ALL":
        return True
    h = ts.hour
    # Broad UTC envelope covering London + New York active windows.
    return 7 <= h < 17


def find_new_fvg(x: pd.DataFrame, i: int, cfg: Config) -> Optional[Zone]:
    # At the first tick of bar i, the newest closed bars are i-1, i-2, i-3.
    if i < 4:
        return None
    n = x.iloc[i-1]  # newest closed
    m = x.iloc[i-2]  # displacement candle
    o = x.iloc[i-3]  # oldest
    a = float(n.atr)
    if not np.isfinite(a) or a <= 0:
        return None
    body = abs(float(m.bid_close-m.bid_open))
    rng = float(m.bid_high-m.bid_low)
    if body < a*cfg.min_body_atr or rng <= 0 or body/rng < cfg.min_body_ratio:
        return None

    if float(o.bid_high) < float(n.bid_low):
        gap = float(n.bid_low-o.bid_high)
        if gap >= a*cfg.min_fvg_atr and float(m.bid_close) > float(m.bid_open):
            return Zone(True, float(o.bid_high), float(n.bid_low), i-1, n.time)
    if float(o.bid_low) > float(n.bid_high):
        gap = float(o.bid_low-n.bid_high)
        if gap >= a*cfg.min_fvg_atr and float(m.bid_close) < float(m.bid_open):
            return Zone(False, float(n.bid_high), float(o.bid_low), i-1, n.time)
    return None


def zone_still_valid(zone: Zone, x: pd.DataFrame, i: int, cfg: Config) -> bool:
    if i-zone.formed_idx > cfg.max_fvg_bars:
        return False
    prev_close = float(x.iloc[i-1].bid_close)
    return prev_close >= zone.low if zone.bullish else prev_close <= zone.high


def rejection_ok(row: pd.Series, bullish: bool) -> bool:
    rng = float(row.bid_high-row.bid_low)
    if rng <= 0:
        return False
    if bullish:
        close_pos = (float(row.bid_close)-float(row.bid_low))/rng
        return close_pos >= 0.55
    close_pos = (float(row.ask_close)-float(row.ask_low))/max(float(row.ask_high-row.ask_low), 1e-12)
    return close_pos <= 0.45


def entry_candidate(row: pd.Series, zone: Zone, cfg: Config) -> Optional[float]:
    # Conservative OHLC approximation of intrabar retest + rejection:
    # require the minute range to touch the FVG and the completed minute to
    # finish with the EA's rejection geometry. If price closes beyond the
    # zone in the favorable direction, assume entry at the worse FVG edge.
    midpoint = (zone.low+zone.high)/2.0
    if zone.bullish:
        touch = float(row.ask_low) <= zone.high and float(row.ask_high) >= zone.low
        if not touch:
            return None
        if cfg.require_rejection and not rejection_ok(row, True):
            return None
        if cfg.require_midpoint and float(row.ask_low) > midpoint:
            return None
        if cfg.require_midpoint:
            return midpoint
        if zone.low <= float(row.ask_close) <= zone.high:
            return float(row.ask_close)
        if float(row.ask_close) > zone.high:
            return zone.high
        return None

    touch = float(row.bid_high) >= zone.low and float(row.bid_low) <= zone.high
    if not touch:
        return None
    if cfg.require_rejection and not rejection_ok(row, False):
        return None
    if cfg.require_midpoint and float(row.bid_high) < midpoint:
        return None
    if cfg.require_midpoint:
        return midpoint
    if zone.low <= float(row.bid_close) <= zone.high:
        return float(row.bid_close)
    if float(row.bid_close) < zone.low:
        return zone.low
    return None


def make_trade(row: pd.Series, i: int, zone: Zone, entry: float, cfg: Config) -> Optional[Trade]:
    atr = float(row.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None
    if zone.bullish:
        sl = zone.low-atr*cfg.sl_atr_buffer
        risk = entry-sl
        if risk <= 0 or risk > atr*cfg.max_sl_atr:
            return None
        tp = entry+risk*cfg.reward_risk
        direction = 1
    else:
        sl = zone.high+atr*cfg.sl_atr_buffer
        risk = sl-entry
        if risk <= 0 or risk > atr*cfg.max_sl_atr:
            return None
        tp = entry-risk*cfg.reward_risk
        direction = -1
    return Trade(direction, i, row.time, entry, sl, tp, risk, zone.low, zone.high)


def manage_trade(t: Trade, x: pd.DataFrame, start: int, cfg: Config) -> int:
    sl = t.sl0
    for j in range(start, len(x)):
        row = x.iloc[j]
        atr = float(row.atr) if np.isfinite(row.atr) else 0.0
        if t.direction == 1:
            adverse = float(row.bid_low)
            favorable = float(row.bid_high)
            close_px = float(row.bid_close)
            t.mae_r = max(t.mae_r, max(0.0, (t.entry-adverse)/t.risk))
            t.mfe_r = max(t.mfe_r, max(0.0, (favorable-t.entry)/t.risk))
            # Conservative intrabar order: existing stop first, then TP.
            if adverse <= sl:
                t.exit_idx, t.exit_time, t.exit_price, t.exit_reason = j, row.time, sl, "SL"
                break
            if favorable >= t.tp:
                t.exit_idx, t.exit_time, t.exit_price, t.exit_reason = j, row.time, t.tp, "TP"
                break
            rr_close = (close_px-t.entry)/t.risk
            if cfg.use_profit_lock and rr_close > 0:
                new_sl = sl
                if rr_close >= cfg.lock2_trigger_r:
                    new_sl = max(new_sl, t.entry+t.risk*cfg.lock2_r)
                elif rr_close >= cfg.lock1_trigger_r:
                    new_sl = max(new_sl, t.entry+t.risk*cfg.lock1_r)
                if rr_close >= cfg.trail_start_r and atr > 0:
                    trail = close_px-atr*cfg.trail_atr
                    floor = t.entry+t.risk*cfg.lock2_r
                    new_sl = max(new_sl, trail, floor)
                sl = new_sl
        else:
            adverse = float(row.ask_high)
            favorable = float(row.ask_low)
            close_px = float(row.ask_close)
            t.mae_r = max(t.mae_r, max(0.0, (adverse-t.entry)/t.risk))
            t.mfe_r = max(t.mfe_r, max(0.0, (t.entry-favorable)/t.risk))
            if adverse >= sl:
                t.exit_idx, t.exit_time, t.exit_price, t.exit_reason = j, row.time, sl, "SL"
                break
            if favorable <= t.tp:
                t.exit_idx, t.exit_time, t.exit_price, t.exit_reason = j, row.time, t.tp, "TP"
                break
            rr_close = (t.entry-close_px)/t.risk
            if cfg.use_profit_lock and rr_close > 0:
                new_sl = sl
                if rr_close >= cfg.lock2_trigger_r:
                    lock = t.entry-t.risk*cfg.lock2_r
                    new_sl = min(new_sl, lock)
                elif rr_close >= cfg.lock1_trigger_r:
                    lock = t.entry-t.risk*cfg.lock1_r
                    new_sl = min(new_sl, lock)
                if rr_close >= cfg.trail_start_r and atr > 0:
                    trail = close_px+atr*cfg.trail_atr
                    floor = t.entry-t.risk*cfg.lock2_r
                    new_sl = min(new_sl, trail, floor)
                sl = new_sl
    else:
        row = x.iloc[-1]
        t.exit_idx, t.exit_time, t.exit_reason = len(x)-1, row.time, "EOD"
        t.exit_price = float(row.bid_close if t.direction == 1 else row.ask_close)

    t.bars = max(1, t.exit_idx-t.entry_idx+1)
    t.r = ((t.exit_price-t.entry)/t.risk)*t.direction
    return t.exit_idx


def run_period(x: pd.DataFrame, cfg: Config) -> list[Trade]:
    if len(x) < 100:
        return []
    bias = bias_series(x, cfg.bias_tf, cfg.bias_fast, cfg.bias_slow) if cfg.use_bias else None
    trades: list[Trade] = []
    zone: Optional[Zone] = None
    latest_zone: Optional[Zone] = None
    i = 60

    while i < len(x):
        newest = find_new_fvg(x, i, cfg)
        if newest is not None:
            latest_zone = newest
            if zone is None or not zone.valid or cfg.replace_with_new_fvg:
                zone = replace(newest)

        if zone is None or not zone.valid:
            if latest_zone is not None and i-latest_zone.formed_idx <= cfg.max_fvg_bars:
                zone = replace(latest_zone)
            else:
                i += 1
                continue

        if not zone_still_valid(zone, x, i, cfg):
            zone.valid = False
            i += 1
            continue
        if cfg.one_trade_per_fvg and zone.traded:
            i += 1
            continue

        row = x.iloc[i]
        if float(row.spread_close) > cfg.max_spread_price:
            i += 1
            continue
        if not session_allowed(row.time, cfg.session_mode):
            i += 1
            continue
        if cfg.use_bias:
            b = bias.iloc[i]
            if not np.isfinite(b) or (zone.bullish and b <= 0) or ((not zone.bullish) and b >= 0):
                i += 1
                continue

        entry = entry_candidate(row, zone, cfg)
        if entry is None:
            i += 1
            continue
        t = make_trade(row, i, zone, entry, cfg)
        if t is None:
            i += 1
            continue
        zone.traded = True
        exit_idx = manage_trade(t, x, i, cfg)
        trades.append(t)
        i = max(i+1, exit_idx+1) if cfg.one_position else i+1

    return trades


def metrics(trades: list[Trade], risk_pct: float = 1.0) -> dict:
    if not trades:
        return {
            "trades": 0, "win_rate": 0.0, "expectancy_r": 0.0, "pf_r": 0.0,
            "net_r": 0.0, "max_dd_pct_at_1pct": 0.0, "ending_equity_1pct": 10000.0,
            "avg_mfe_r": 0.0, "avg_mae_r": 0.0, "median_r": 0.0,
            "tp": 0, "sl": 0, "eod": 0,
        }
    rs = np.array([t.r for t in trades], dtype=float)
    wins = rs[rs > 0]
    losses = rs[rs < 0]
    pf = float(wins.sum()/abs(losses.sum())) if len(losses) and losses.sum() < 0 else (999.0 if len(wins) else 0.0)

    eq = 10000.0
    peak = eq
    maxdd = 0.0
    for r in rs:
        eq *= max(0.0, 1.0 + (risk_pct/100.0)*r)
        peak = max(peak, eq)
        if peak > 0:
            maxdd = max(maxdd, (peak-eq)/peak*100.0)

    reasons = pd.Series([t.exit_reason for t in trades]).value_counts().to_dict()
    return {
        "trades": int(len(trades)),
        "win_rate": float((rs > 0).mean()*100.0),
        "expectancy_r": float(rs.mean()),
        "pf_r": pf,
        "net_r": float(rs.sum()),
        "max_dd_pct_at_1pct": float(maxdd),
        "ending_equity_1pct": float(eq),
        "avg_mfe_r": float(np.mean([t.mfe_r for t in trades])),
        "avg_mae_r": float(np.mean([t.mae_r for t in trades])),
        "median_r": float(np.median(rs)),
        "tp": int(reasons.get("TP", 0)),
        "sl": int(reasons.get("SL", 0)),
        "eod": int(reasons.get("EOD", 0)),
    }


def variants() -> list[Config]:
    base = Config(name="ORIGINAL_LOGIC_RR30")
    return [
        replace(base, name="ORIGINAL_3DIGIT_SPREAD", max_spread_price=0.08),
        base,
        replace(base, name="RR5", reward_risk=5.0),
        replace(base, name="RR3", reward_risk=3.0),
        replace(base, name="RR2", reward_risk=2.0),
        replace(base, name="RR3_NO_REJECTION", reward_risk=3.0, require_rejection=False),
        replace(base, name="RR3_MIDPOINT", reward_risk=3.0, require_midpoint=True),
        replace(base, name="RR3_M5_BIAS", reward_risk=3.0, use_bias=True, bias_tf="5min"),
        replace(base, name="RR3_M15_BIAS", reward_risk=3.0, use_bias=True, bias_tf="15min"),
        replace(base, name="RR3_LONDON_NY", reward_risk=3.0, session_mode="LONDON_NY_UTC"),
        replace(base, name="RR3_NO_LOCK", reward_risk=3.0, use_profit_lock=False),
        replace(base, name="RR5_NO_LOCK", reward_risk=5.0, use_profit_lock=False),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="research_data")
    ap.add_argument("--output", default="fvg_scalper_results")
    ap.add_argument("--split", default="2026-04-20")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    x = load_data(Path(args.root))
    split = pd.Timestamp(args.split, tz="UTC")
    ins = x[x["time"] < split].reset_index(drop=True)
    oos = x[x["time"] >= split].reset_index(drop=True)

    rows = []
    all_trades = []
    for cfg in variants():
        for label, frame in (("IS", ins), ("OOS", oos), ("ALL", x)):
            ts = run_period(frame, cfg)
            m = metrics(ts)
            rows.append({"variant": cfg.name, "sample": label, **m})
            for t in ts:
                d = asdict(t)
                d.update({"variant": cfg.name, "sample": label})
                all_trades.append(d)

    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False)
    pd.DataFrame(all_trades).to_csv(out / "trades.csv", index=False)

    # Rank only on in-sample expectancy with basic sample-size guard, then
    # show OOS separately; do not optimize against OOS.
    is_rank = summary[summary["sample"] == "IS"].copy()
    is_rank["eligible"] = is_rank["trades"] >= 30
    is_rank = is_rank.sort_values(["eligible", "expectancy_r", "pf_r"], ascending=[False, False, False])
    oos_map = summary[summary["sample"] == "OOS"].set_index("variant")

    report = {
        "data_first": str(x["time"].iloc[0]),
        "data_last": str(x["time"].iloc[-1]),
        "rows_active": int(len(x)),
        "split": str(split),
        "method": "M1 bid/ask OHLC conservative intrabar proxy; native MT5 confirmation required",
        "ranked_is": [],
    }
    for _, r in is_rank.iterrows():
        o = oos_map.loc[r["variant"]]
        report["ranked_is"].append({
            "variant": r["variant"],
            "is": {k: (int(r[k]) if k in ("trades","tp","sl","eod") else float(r[k]))
                   for k in ["trades","win_rate","expectancy_r","pf_r","net_r","max_dd_pct_at_1pct","avg_mfe_r","avg_mae_r","tp","sl","eod"]},
            "oos": {k: (int(o[k]) if k in ("trades","tp","sl","eod") else float(o[k]))
                    for k in ["trades","win_rate","expectancy_r","pf_r","net_r","max_dd_pct_at_1pct","avg_mfe_r","avg_mae_r","tp","sl","eod"]},
        })
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(summary.to_string(index=False))
    print("\nRANKED_IN_SAMPLE")
    for item in report["ranked_is"]:
        print(json.dumps(item, separators=(",", ":")))


if __name__ == "__main__":
    main()
