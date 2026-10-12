from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
from typing import Any

import numpy as np
import pandas as pd

FIDELITY = "M1_BAR_APPROX_CAUSAL_NEXT_BAR_ENTRY"
LIMITATIONS = (
    "M1 bar approximation only: no native MT5 tick sequencing, intrabar rejection sequencing, "
    "broker margin/lot rounding, or stop/freeze-level reproduction."
)


@dataclass(frozen=True)
class Params:
    min_fvg_atr: float = 0.15
    min_body_atr: float = 0.50
    min_body_ratio: float = 0.60
    max_fvg_bars: int = 1000
    replace_with_new_fvg: bool = True
    one_trade_per_fvg: bool = False
    use_bias_filter: bool = False
    require_midpoint: bool = False
    require_rejection: bool = True
    reward_risk: float = 30.0
    max_sl_atr: float = 3.0
    atr_period: int = 14
    sl_atr_buffer: float = 0.15
    use_profit_lock: bool = True
    lock1_trigger_rr: float = 0.50
    lock1_rr: float = 0.10
    lock2_trigger_rr: float = 1.0
    lock2_rr: float = 0.35
    use_atr_trail: bool = True
    trail_start_rr: float = 1.5
    trail_atr: float = 0.10
    max_spread_price: float = 0.80
    max_trades_day: int = 1000
    cooldown_bars: int = 0
    max_attempts_per_fvg: int | None = None


@dataclass(eq=True)
class Zone:
    bullish: bool
    low: float
    high: float
    formed_i: int
    formed_time: pd.Timestamp
    traded: bool = False
    zone_id: str = ""
    attempts: int = 0
    last_entry_i: int | None = None


@dataclass
class Trade:
    zone_id: str
    attempt_no: int
    time_since_prior_attempt_bars: int | None
    fvg_age_bars: int
    fvg_width_atr: float
    fill_depth: float
    rejection_strength: float
    direction: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_i: int
    exit_i: int
    bullish: bool
    entry: float
    initial_stop: float
    target: float
    exit: float
    realized_r: float
    mfe_r: float
    mae_r: float
    exit_reason: str
    hold_bars: int
    entry_spread: float


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev = df["mid_close"].shift(1)
    return pd.concat(
        [
            (df["mid_high"] - df["mid_low"]).abs(),
            (df["mid_high"] - prev).abs(),
            (df["mid_low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)


def prepare(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    x = df.sort_values("time").reset_index(drop=True).copy()
    tr = _true_range(x)
    # atr_close[i] is available only after bar i closes; atr[i] is the value
    # available at the open of bar i and therefore cannot contain bar i.
    x["atr_close"] = tr.ewm(alpha=1 / p.atr_period, adjust=False, min_periods=p.atr_period).mean()
    x["atr"] = x["atr_close"].shift(1)
    return x


def zone_identity(bullish: bool, formed_time: pd.Timestamp, low: float, high: float) -> str:
    payload = f"{1 if bullish else 0}|{pd.Timestamp(formed_time).isoformat()}|{low:.10f}|{high:.10f}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def find_newest_fvg(x: pd.DataFrame, decision_i: int, p: Params) -> Zone | None:
    """Return the FVG formed by the three fully closed bars ending at i-1."""
    if decision_i < 3:
        return None
    old_i, mid_i, new_i = decision_i - 3, decision_i - 2, decision_i - 1
    a = float(x.loc[mid_i, "atr"])
    if not np.isfinite(a) or a <= 0:
        return None

    old_high = float(x.loc[old_i, "mid_high"])
    old_low = float(x.loc[old_i, "mid_low"])
    mo = float(x.loc[mid_i, "mid_open"])
    mc = float(x.loc[mid_i, "mid_close"])
    mh = float(x.loc[mid_i, "mid_high"])
    ml = float(x.loc[mid_i, "mid_low"])
    new_high = float(x.loc[new_i, "mid_high"])
    new_low = float(x.loc[new_i, "mid_low"])
    body = abs(mc - mo)
    rng = mh - ml
    if body < a * p.min_body_atr or rng <= 0 or body / rng < p.min_body_ratio:
        return None

    formed_time = pd.Timestamp(x.loc[new_i, "time"])
    if old_high < new_low:
        gap = new_low - old_high
        if gap >= a * p.min_fvg_atr and mc > mo:
            return Zone(
                True,
                old_high,
                new_low,
                new_i,
                formed_time,
                zone_id=zone_identity(True, formed_time, old_high, new_low),
            )
    if old_low > new_high:
        gap = old_low - new_high
        if gap >= a * p.min_fvg_atr and mc < mo:
            return Zone(
                False,
                new_high,
                old_low,
                new_i,
                formed_time,
                zone_id=zone_identity(False, formed_time, new_high, old_low),
            )
    return None


def rejection_ok(x: pd.DataFrame, decision_i: int, bullish: bool) -> tuple[bool, float]:
    """Evaluate rejection only on the fully closed bar i-1."""
    if decision_i < 1:
        return False, 0.0
    i = decision_i - 1
    low = float(x.loc[i, "mid_low"])
    high = float(x.loc[i, "mid_high"])
    close = float(x.loc[i, "mid_close"])
    rng = high - low
    if rng <= 0:
        return False, 0.0
    close_pos = (close - low) / rng
    if bullish:
        return close_pos >= 0.55, float(close_pos)
    strength = 1.0 - close_pos
    return close_pos <= 0.45, float(strength)


def reentry_allowed(zone: Zone, entry_i: int, p: Params) -> bool:
    if p.one_trade_per_fvg and zone.attempts >= 1:
        return False
    if p.max_attempts_per_fvg is not None and zone.attempts >= p.max_attempts_per_fvg:
        return False
    if p.cooldown_bars > 0 and zone.last_entry_i is not None:
        if entry_i - zone.last_entry_i <= p.cooldown_bars:
            return False
    return True


_BASE_A01 = Params(one_trade_per_fvg=False, cooldown_bars=0, max_attempts_per_fvg=None)
A01_POLICIES = {
    "A01_CONTROL": _BASE_A01,
    "A01_ONE_TRADE": replace(_BASE_A01, one_trade_per_fvg=True),
    "A01_COOLDOWN_1BAR": replace(_BASE_A01, cooldown_bars=1),
    "A01_MAX3": replace(_BASE_A01, max_attempts_per_fvg=3),
}


def next_stop_after_closed_bar(position: dict[str, Any], mark: float, atr: float, bullish: bool, p: Params) -> float:
    entry = float(position["entry"])
    risk = float(position["risk"])
    current = float(position["stop"])
    if risk <= 0:
        return current
    rr = (mark - entry) / risk if bullish else (entry - mark) / risk
    candidate = current
    if p.use_profit_lock:
        lock_r: float | None = None
        if rr >= p.lock2_trigger_rr:
            lock_r = p.lock2_rr
        elif rr >= p.lock1_trigger_rr:
            lock_r = p.lock1_rr
        if lock_r is not None:
            lock_stop = entry + risk * lock_r if bullish else entry - risk * lock_r
            candidate = max(candidate, lock_stop) if bullish else min(candidate, lock_stop)
    if p.use_atr_trail and rr >= p.trail_start_rr and atr > 0:
        trail = mark - atr * p.trail_atr if bullish else mark + atr * p.trail_atr
        floor = entry + risk * p.lock2_rr if bullish else entry - risk * p.lock2_rr
        trail = max(trail, floor) if bullish else min(trail, floor)
        candidate = max(candidate, trail) if bullish else min(candidate, trail)
    return float(candidate)


def resolve_bar_exit(
    position: dict[str, Any],
    *,
    bid_low: float,
    bid_high: float,
    ask_low: float,
    ask_high: float,
    bullish: bool,
) -> tuple[float, str] | None:
    stop = float(position["stop"])
    target = float(position["target"])
    if bullish:
        stop_hit = bid_low <= stop
        target_hit = bid_high >= target
    else:
        stop_hit = ask_high >= stop
        target_hit = ask_low <= target
    # Conservative bar-ordering rule when both were touched.
    if stop_hit:
        return stop, "SL"
    if target_hit:
        return target, "TP"
    return None


def _basic_metrics(trades: list[Trade]) -> dict[str, Any]:
    rs = np.asarray([t.realized_r for t in trades], dtype=float)
    if len(rs) == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "net_r": 0.0,
            "average_win_r": 0.0,
            "average_loss_r": 0.0,
            "max_drawdown_r": 0.0,
            "max_loss_streak": 0,
        }
    pos = rs[rs > 0]
    neg = rs[rs < 0]
    gp = float(pos.sum())
    gl = float(-neg.sum())
    eq = np.r_[0.0, rs.cumsum()]
    dd = np.maximum.accumulate(eq) - eq
    best = cur = 0
    for r in rs:
        cur = cur + 1 if r < 0 else 0
        best = max(best, cur)
    return {
        "trades": int(len(rs)),
        "wins": int((rs > 0).sum()),
        "losses": int((rs < 0).sum()),
        "win_rate": float((rs > 0).mean()),
        "profit_factor": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0),
        "expectancy_r": float(rs.mean()),
        "net_r": float(rs.sum()),
        "average_win_r": float(pos.mean()) if len(pos) else 0.0,
        "average_loss_r": float(neg.mean()) if len(neg) else 0.0,
        "max_drawdown_r": float(dd.max()),
        "max_loss_streak": int(best),
    }


def metrics(trades: list[Trade]) -> dict[str, Any]:
    out = _basic_metrics(trades)
    attempts: dict[str, dict[str, Any]] = {}
    for n in sorted({t.attempt_no for t in trades}):
        attempts[str(n)] = _basic_metrics([t for t in trades if t.attempt_no == n])
    out["attempt_breakdown"] = attempts
    return out


def trades_frame(trades: list[Trade]) -> pd.DataFrame:
    return pd.DataFrame([asdict(t) for t in trades])


def _update_excursions(position: dict[str, Any], row: pd.Series) -> None:
    entry = float(position["entry"])
    risk = float(position["risk"])
    if position["bullish"]:
        favorable = (float(row["bid_high"]) - entry) / risk
        adverse = (entry - float(row["bid_low"])) / risk
    else:
        favorable = (entry - float(row["ask_low"])) / risk
        adverse = (float(row["ask_high"]) - entry) / risk
    position["mfe_r"] = max(float(position["mfe_r"]), float(favorable), 0.0)
    position["mae_r"] = max(float(position["mae_r"]), float(adverse), 0.0)


def _finalize(position: dict[str, Any], exit_i: int, exit_time: pd.Timestamp, exit_px: float, reason: str) -> Trade:
    entry = float(position["entry"])
    risk = float(position["risk"])
    bullish = bool(position["bullish"])
    rr = (exit_px - entry) / risk if bullish else (entry - exit_px) / risk
    return Trade(
        zone_id=position["zone_id"],
        attempt_no=position["attempt_no"],
        time_since_prior_attempt_bars=position["time_since_prior_attempt_bars"],
        fvg_age_bars=position["fvg_age_bars"],
        fvg_width_atr=position["fvg_width_atr"],
        fill_depth=position["fill_depth"],
        rejection_strength=position["rejection_strength"],
        direction="LONG" if bullish else "SHORT",
        entry_time=position["entry_time"],
        exit_time=exit_time,
        entry_i=position["entry_i"],
        exit_i=exit_i,
        bullish=bullish,
        entry=entry,
        initial_stop=position["initial_stop"],
        target=position["target"],
        exit=float(exit_px),
        realized_r=float(rr),
        mfe_r=float(position["mfe_r"]),
        mae_r=float(position["mae_r"]),
        exit_reason=reason,
        hold_bars=int(exit_i - position["entry_i"] + 1),
        entry_spread=float(position["entry_spread"]),
    )


def run(df: pd.DataFrame, p: Params) -> tuple[list[Trade], dict[str, Any]]:
    if len(df) < 4:
        return [], {**metrics([]), "fidelity": FIDELITY, "compounding": False, "limitations": LIMITATIONS}
    if {"atr", "atr_close"}.issubset(df.columns):
        x = df.sort_values("time").reset_index(drop=True).copy()
    else:
        x = prepare(df, p)

    zone: Zone | None = None
    position: dict[str, Any] | None = None
    trades: list[Trade] = []
    current_day = None
    trades_day = 0

    for i in range(3, len(x)):
        row = x.iloc[i]
        day = pd.Timestamp(row["time"]).date()
        if day != current_day:
            current_day = day
            trades_day = 0

        # At bar open, the just-closed i-1 bar may define a new zone.
        candidate = find_newest_fvg(x, i, p)
        if candidate is not None:
            if zone is None or (
                p.replace_with_new_fvg and candidate.formed_time > zone.formed_time
            ):
                zone = candidate

        had_position_at_open = position is not None
        if position is not None:
            _update_excursions(position, row)
            hit = resolve_bar_exit(
                position,
                bid_low=float(row["bid_low"]),
                bid_high=float(row["bid_high"]),
                ask_low=float(row["ask_low"]),
                ask_high=float(row["ask_high"]),
                bullish=bool(position["bullish"]),
            )
            if hit is not None:
                exit_px, reason = hit
                trades.append(_finalize(position, i, pd.Timestamp(row["time"]), exit_px, reason))
                position = None
            else:
                mark = float(row["bid_close"] if position["bullish"] else row["ask_close"])
                atr_close = float(row.get("atr_close", row["atr"]))
                if np.isfinite(atr_close) and atr_close > 0:
                    position["stop"] = next_stop_after_closed_bar(position, mark, atr_close, bool(position["bullish"]), p)

        # Bar approximation cannot know whether an intrabar exit preceded another
        # possible entry tick, so do not re-enter on a bar that began with a position.
        if had_position_at_open or position is not None:
            continue
        if zone is None or trades_day >= p.max_trades_day:
            continue
        if i - zone.formed_i > p.max_fvg_bars:
            zone = None
            continue

        prev_close = float(x.loc[i - 1, "mid_close"])
        if (zone.bullish and prev_close < zone.low) or ((not zone.bullish) and prev_close > zone.high):
            zone = None
            continue
        if not reentry_allowed(zone, i, p):
            continue

        spread = float(row["spread_open"])
        if not np.isfinite(spread) or spread > p.max_spread_price:
            continue
        rejection, rejection_strength = rejection_ok(x, i, zone.bullish)
        if p.require_rejection and not rejection:
            continue

        price = float(row["ask_open"] if zone.bullish else row["bid_open"])
        if not (zone.low <= price <= zone.high):
            continue
        midpoint = (zone.low + zone.high) / 2.0
        if p.require_midpoint:
            if zone.bullish and price > midpoint:
                continue
            if (not zone.bullish) and price < midpoint:
                continue

        a = float(row["atr"])
        if not np.isfinite(a) or a <= 0:
            continue
        if zone.bullish:
            stop = zone.low - a * p.sl_atr_buffer
            risk = price - stop
            target = price + risk * p.reward_risk
        else:
            stop = zone.high + a * p.sl_atr_buffer
            risk = stop - price
            target = price - risk * p.reward_risk
        if risk <= 0 or risk > a * p.max_sl_atr:
            continue

        width = zone.high - zone.low
        if width <= 0:
            continue
        fill_depth = (zone.high - price) / width if zone.bullish else (price - zone.low) / width
        prior_entry_i = zone.last_entry_i
        attempt_no = zone.attempts + 1
        zone.attempts = attempt_no
        zone.last_entry_i = i
        zone.traded = True
        trades_day += 1

        position = {
            "zone_id": zone.zone_id,
            "attempt_no": attempt_no,
            "time_since_prior_attempt_bars": None if prior_entry_i is None else i - prior_entry_i,
            "fvg_age_bars": i - zone.formed_i,
            "fvg_width_atr": width / a,
            "fill_depth": float(fill_depth),
            "rejection_strength": float(rejection_strength),
            "entry_time": pd.Timestamp(row["time"]),
            "entry_i": i,
            "bullish": zone.bullish,
            "entry": price,
            "initial_stop": float(stop),
            "stop": float(stop),
            "target": float(target),
            "risk": float(risk),
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "entry_spread": spread,
        }

        # Entry occurs at the bar open; the rest of this bar may hit stop/target.
        _update_excursions(position, row)
        hit = resolve_bar_exit(
            position,
            bid_low=float(row["bid_low"]),
            bid_high=float(row["bid_high"]),
            ask_low=float(row["ask_low"]),
            ask_high=float(row["ask_high"]),
            bullish=zone.bullish,
        )
        if hit is not None:
            exit_px, reason = hit
            trades.append(_finalize(position, i, pd.Timestamp(row["time"]), exit_px, reason))
            position = None
        else:
            mark = float(row["bid_close"] if zone.bullish else row["ask_close"])
            atr_close = float(row.get("atr_close", a))
            if np.isfinite(atr_close) and atr_close > 0:
                position["stop"] = next_stop_after_closed_bar(position, mark, atr_close, zone.bullish, p)

    if position is not None:
        i = len(x) - 1
        row = x.iloc[i]
        _update_excursions(position, row)
        exit_px = float(row["bid_close"] if position["bullish"] else row["ask_close"])
        trades.append(_finalize(position, i, pd.Timestamp(row["time"]), exit_px, "EOD"))

    report = metrics(trades)
    report.update(
        {
            "fidelity": FIDELITY,
            "compounding": False,
            "limitations": LIMITATIONS,
            "params": asdict(p),
        }
    )
    return trades, report
