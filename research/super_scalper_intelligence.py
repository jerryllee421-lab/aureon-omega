#!/usr/bin/env python3
"""AUREON Ω V9.4 Super Scalper Intelligence.

Research/DEMO decision intelligence only. This module never submits broker orders.
It converts a frozen higher-timeframe edge context plus M1 execution evidence into
a deterministic readiness state and score.

States:
  BLOCKED  hard safety/data/cost gate failed
  WATCH    valid market context but no executable microstructure yet
  ARMED    strong setup; waiting for final trigger
  TRIGGERED all gates satisfied and micro trigger present

The score is readiness, NOT win probability.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class ScalperState(str, Enum):
    BLOCKED = "BLOCKED"
    WATCH = "WATCH"
    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"


@dataclass(frozen=True)
class ScalperInput:
    # Frozen/proven context
    context_qualified: bool
    rsi_extreme: bool
    sweep_reclaim: bool
    extension_atr: float
    adx: float
    vol_ratio: float
    minutes_from_anchor: float

    # M1 execution evidence
    m1_mss: bool
    m1_displacement_atr: float
    m1_fvg_retest: bool
    m1_micro_break: bool
    m1_reclaim: bool

    # Evidence-derived expectancy/cost
    gross_edge_r: float
    spread_cost_r: float
    slippage_cost_r: float

    # Execution/data safety
    stale_seconds: float
    latency_ms: float
    open_positions: int = 0
    daily_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    daily_loss_limit: float = 3.0
    drawdown_limit: float = 6.0


@dataclass(frozen=True)
class ScalperDecision:
    state: ScalperState
    readiness: int
    net_edge_r: float
    reasons: tuple[str, ...]
    contradictions: tuple[str, ...]
    components: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["state"] = self.state.value
        return out


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _context_score(x: ScalperInput) -> int:
    if not x.context_qualified:
        return 0
    score = 10
    score += 8 if x.sweep_reclaim else 0
    score += 5 if x.rsi_extreme else 0
    score += round(6 * _clamp((x.extension_atr - 1.5) / 1.5, 0.0, 1.0))
    score += round(4 * _clamp((30.0 - x.adx) / 12.0, 0.0, 1.0))
    score += 2 if 0.80 <= x.vol_ratio < 1.80 else 0
    return min(35, score)


def _micro_score(x: ScalperInput) -> int:
    score = 0
    score += 9 if x.m1_mss else 0
    score += round(8 * _clamp(x.m1_displacement_atr / 1.0, 0.0, 1.0))
    score += 6 if x.m1_fvg_retest else 0
    score += 4 if x.m1_micro_break else 0
    score += 3 if x.m1_reclaim else 0
    return min(30, score)


def _timing_score(x: ScalperInput) -> int:
    age = x.minutes_from_anchor
    if age < 0:
        return 0
    if age <= 10:
        return 15
    if age <= 20:
        return 13
    if age <= 30:
        return 10
    if age <= 45:
        return 6
    if age <= 60:
        return 3
    return 0


def _execution_score(x: ScalperInput) -> int:
    cost_r = max(0.0, x.spread_cost_r) + max(0.0, x.slippage_cost_r)
    cost_points = round(12 * _clamp(1.0 - cost_r / 0.20, 0.0, 1.0))
    freshness = 4 if x.stale_seconds <= 1.0 else 2 if x.stale_seconds <= 2.0 else 0
    latency = 4 if x.latency_ms <= 150 else 2 if x.latency_ms <= 350 else 0
    return min(20, cost_points + freshness + latency)


def decide(x: ScalperInput, *, trigger_threshold: int = 82, arm_threshold: int = 65,
           min_net_edge_r: float = 0.05) -> ScalperDecision:
    reasons: list[str] = []
    contradictions: list[str] = []

    hard_blocks: list[str] = []
    if not x.context_qualified:
        hard_blocks.append("NO_FROZEN_CONTEXT")
    if x.stale_seconds > 3.0:
        hard_blocks.append("STALE_MARKET_DATA")
    if x.open_positions > 0:
        hard_blocks.append("POSITION_EXISTS")
    if x.daily_loss_pct >= x.daily_loss_limit:
        hard_blocks.append("DAILY_LOSS_LIMIT")
    if x.drawdown_pct >= x.drawdown_limit:
        hard_blocks.append("DRAWDOWN_LIMIT")
    if not (0.80 <= x.vol_ratio < 1.80):
        hard_blocks.append("VOLATILITY_REGIME")
    if x.minutes_from_anchor > 60.0:
        hard_blocks.append("ANCHOR_EXPIRED")

    net_edge_r = x.gross_edge_r - x.spread_cost_r - x.slippage_cost_r
    if net_edge_r < min_net_edge_r:
        hard_blocks.append("NET_EDGE_BELOW_FLOOR")

    components = {
        "context": _context_score(x),
        "microstructure": _micro_score(x),
        "timing": _timing_score(x),
        "execution": _execution_score(x),
    }
    readiness = min(100, sum(components.values()))

    if x.adx > 30:
        contradictions.append("ADX_TOO_HIGH_FOR_EXHAUSTION_CONTROL")
    if x.extension_atr < 2.0:
        contradictions.append("INSUFFICIENT_EXTENSION")
    if not x.sweep_reclaim:
        contradictions.append("NO_LIQUIDITY_FAILURE")
    if x.spread_cost_r + x.slippage_cost_r > 0.15:
        contradictions.append("HIGH_EXECUTION_COST")
    if x.minutes_from_anchor > 30:
        contradictions.append("LATE_ENTRY_DECAY")

    final_trigger = (
        x.m1_mss
        and x.m1_displacement_atr >= 0.50
        and (x.m1_fvg_retest or x.m1_reclaim)
        and x.m1_micro_break
    )

    if hard_blocks:
        return ScalperDecision(
            ScalperState.BLOCKED, readiness, net_edge_r,
            tuple(hard_blocks), tuple(contradictions), components
        )

    if readiness >= trigger_threshold and final_trigger:
        reasons += ["FROZEN_CONTEXT_VALID", "M1_TRIGGER_COMPLETE", "NET_EDGE_POSITIVE"]
        state = ScalperState.TRIGGERED
    elif readiness >= arm_threshold:
        reasons += ["FROZEN_CONTEXT_VALID", "AWAIT_FINAL_MICRO_TRIGGER"]
        state = ScalperState.ARMED
    else:
        reasons += ["FROZEN_CONTEXT_VALID", "MICROSTRUCTURE_NOT_READY"]
        state = ScalperState.WATCH

    return ScalperDecision(
        state, readiness, net_edge_r,
        tuple(reasons), tuple(contradictions), components
    )
