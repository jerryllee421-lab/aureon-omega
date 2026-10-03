# AUREON Ω V9.4 — Super Scalper Intelligence

## Objective

Convert a validated Gold setup into a fast, deterministic execution-readiness decision without turning ASTRA into indicator soup.

## Intelligence hierarchy

1. **M5 frozen edge context** — liquidity sweep/reclaim, RSI exhaustion, >=2 ATR extension from EMA21, ADX <=30, accepted volatility regime.
2. **M1 precision layer** — MSS, displacement, FVG/retest or reclaim, micro break.
3. **Timing decay** — highest readiness immediately after the M5 anchor; readiness decays as the anchor ages.
4. **Execution economics** — empirical gross edge minus spread/slippage cost. A setup is blocked if estimated net edge falls below the configured floor.
5. **Risk vetoes** — stale data, existing position, daily-loss breach, drawdown breach, invalid volatility regime, expired anchor.

## State machine

BLOCKED -> hard veto / insufficient net edge
WATCH   -> context valid, microstructure weak
ARMED   -> setup strong, final M1 trigger incomplete
TRIGGERED -> context + micro trigger + cost/risk gates all valid

The readiness score is NOT a win probability.

## Calibration rule

Component weights are provisional engineering weights. They must be calibrated against V9.3/V9.4 event evidence and may not be advertised as probability/confidence until reliability calibration is demonstrated on untouched data.

## Promotion

Super Scalper Intelligence is allowed to improve entry selection only if it beats the frozen V7/V9 control after:
- chronological validation and untouched holdout
- half-year stability
- spread/slippage stress
- parameter-neighborhood tests
- native MT5 real ticks
- DEMO forward parity

Research/DEMO only. No LIVE authorization.
