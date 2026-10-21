"""Deterministic quote-level execution primitives for offline XAUUSD research.

Signals must be produced from completed bars before signal_time. This module
only simulates subsequent quote execution; it does not generate signals or
certify broker-native execution.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    side: int
    entry_time: Optional[pd.Timestamp] = None
    exit_time: Optional[pd.Timestamp] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    reason: Optional[str] = None
    gross_price_units: Optional[float] = None
    entry_spread: Optional[float] = None
    exit_spread: Optional[float] = None


def simulate_quote_exit(
    ticks: pd.DataFrame,
    signal_time,
    side: int,
    stop_price: float,
    target_price: float,
    *,
    max_entry_spread: float = 0.80,
    max_quote_gap_seconds: float = 60.0,
    slippage_price_units: float = 0.35,
) -> ExecutionResult:
    """Enter on first quote after signal_time, then resolve SL/TP in quote order.

    Long entries execute at ask and exits at bid; shorts enter at bid and exit
    at ask. A stop crossed through a gap receives adverse slippage. A target
    fills at its target level or a better executable quote. Stale entry quotes
    are rejected. If no exit triggers, the position is marked at the final
    executable quote and status is END_OF_DATA_MARK (not a closed trade).
    """
    if side not in (-1, 1):
        raise ValueError("side must be +1 (long) or -1 (short)")
    if max_entry_spread < 0 or max_quote_gap_seconds <= 0 or slippage_price_units < 0:
        raise ValueError("invalid execution limits")
    required = {"timestamp", "bid", "ask"}
    if not required.issubset(ticks.columns):
        raise ValueError("ticks must contain timestamp, bid, ask")
    q = ticks.loc[:, ["timestamp", "bid", "ask"]].copy()
    q["timestamp"] = pd.to_datetime(q["timestamp"], utc=True, errors="coerce")
    q["bid"] = pd.to_numeric(q["bid"], errors="coerce")
    q["ask"] = pd.to_numeric(q["ask"], errors="coerce")
    q = q.dropna().sort_values("timestamp")
    q = q[(q["bid"] > 0) & (q["ask"] >= q["bid"])].drop_duplicates(
        ["timestamp", "bid", "ask"]
    )
    signal_time = pd.to_datetime(signal_time, utc=True)
    q = q[q["timestamp"] > signal_time].reset_index(drop=True)
    if q.empty:
        return ExecutionResult("NO_ENTRY_QUOTE", side)
    first = q.iloc[0]
    spread = float(first.ask - first.bid)
    gap = (first.timestamp - signal_time).total_seconds()
    if gap > max_quote_gap_seconds:
        return ExecutionResult("REJECTED_STALE_ENTRY", side)
    if spread > max_entry_spread:
        return ExecutionResult("REJECTED_WIDE_SPREAD", side)
    entry = float(first.ask if side == 1 else first.bid)
    for row in q.iloc[1:].itertuples(index=False):
        prev_time = q.loc[q.timestamp < row.timestamp, "timestamp"].iloc[-1]
        if (row.timestamp - prev_time).total_seconds() > max_quote_gap_seconds:
            exit_px = float(row.bid if side == 1 else row.ask)
            gross = (exit_px - entry) * side
            return ExecutionResult(
                "GAP_MARK", side, first.timestamp, row.timestamp, entry, exit_px,
                "QUOTE_GAP", gross, spread, float(row.ask - row.bid)
            )
        executable = float(row.bid if side == 1 else row.ask)
        stop_hit = executable <= stop_price if side == 1 else executable >= stop_price
        target_hit = executable >= target_price if side == 1 else executable <= target_price
        if stop_hit:
            # Adverse slippage is applied beyond the executable quote on stop.
            exit_px = executable - slippage_price_units if side == 1 else executable + slippage_price_units
            return ExecutionResult(
                "CLOSED", side, first.timestamp, row.timestamp, entry, exit_px,
                "SL", (exit_px - entry) * side, spread, float(row.ask - row.bid)
            )
        if target_hit:
            exit_px = max(target_price, executable) if side == 1 else min(target_price, executable)
            return ExecutionResult(
                "CLOSED", side, first.timestamp, row.timestamp, entry, exit_px,
                "TP", (exit_px - entry) * side, spread, float(row.ask - row.bid)
            )
    last = q.iloc[-1]
    exit_px = float(last.bid if side == 1 else last.ask)
    return ExecutionResult(
        "END_OF_DATA_MARK", side, first.timestamp, last.timestamp, entry, exit_px,
        "END_OF_DATA_MARK", (exit_px - entry) * side, spread, float(last.ask-last.bid)
    )
