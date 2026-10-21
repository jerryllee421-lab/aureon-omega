# Adaptive Prediction Engine (research-only)

## Purpose
This module adds a leakage-aware, regime-conditioned empirical forecast to the
existing Gold research loop. It does not place orders, connect to a broker, or
authorize execution. It is a baseline for measurement—not a claim of predictive
accuracy or profitability.

## Input contract
Pass chronological, completed OHLC bars as mappings with positive `high`,
`low`, and `close`; `time` is optional but must be strictly increasing when
provided. The caller must ensure broker timestamps, symbol identity, candle
closure and data integrity have already been validated.

## Method
- Features use only bars at or before each feature timestamp: 3-bar and 12-bar
  momentum normalized by a 20-bar true-range ATR, plus short/long volatility.
- Analogues are bucketed by short momentum direction and volatility regime.
- Forward labels use the requested horizon and a configurable return-cost floor.
- Training examples are purged: an example is eligible only when its entire
  future label horizon ends strictly before the forecast index.
- Class probabilities are empirical conditional frequencies smoothed toward the
  global historical prior. Small samples or weak direction trigger ABSTAIN.
- The result includes expected return, expected move in ATR units, sample counts,
  regime, abstention reasons and explicit research-only authority flags.

## Limits and promotion gates
These are empirical frequencies, not automatically calibrated probabilities.
Evaluate calibration on untouched, rolling holdouts; report Brier score/log loss,
coverage, conditional sample counts, spread/slippage sensitivity, and net
expectancy. Compare against simple baselines and V2.12 control using identical
data and costs. Run ablations, regime/direction/session breakdowns and
multiple-testing-aware selection. Never tune on the final holdout.

The module must not be used to route orders. Promotion to a DEMO research lane
requires native MT5 real-tick testing, broker-specific cost stress, and separate
execution/risk certification. Live-money execution remains blocked.
