# AUREON Ω — Strategy Intelligence Research Layer

Status: research-only, not deployment-approved.

## Purpose
The context scorer ranks candidate evidence from structure, liquidity sweep/reclaim, displacement, candle patterns, support/resistance and trendline breaks. It adds a past-only EMA trend regime and ATR-based volatility regime. Scores are weighted evidence points, not probabilities or an AI prediction.

## Decision controls
- Warm-up history is mandatory; otherwise abstain.
- Weak scores and conflicting long/short scores produce abstention.
- Candidate output carries `research_only=true` and `trade_authorized=false`.
- No broker order, lot sizing or live-trading path is implemented by this module.
- Candidate signal logic must be evaluated separately by variant; the combined score must not conceal weak components.

## Required evaluation
1. Verify causal feature timing and no future leakage.
2. Measure each isolated setup: BOS continuation, CHoCH reversal, sweep/reclaim, support/resistance, trendline break and candle pattern.
3. Use the same quote execution, stop/target and cost rules for all variants.
4. Report closed trade count, net expectancy, PF, max equity drawdown, exposure, confidence intervals and OOS metrics.
5. Run cost stress and anchored walk-forward folds; reserve a final holdout.
6. Reproduce finalists in MT5 Strategy Tester using broker-native Every Tick Based on Real Ticks and verified PXBT economics.

## Data gate
The currently documented October 2026 archive is third-party Dukascopy data, not verified PXBTTrading-1 native data, and covers roughly 20 days. It is insufficient to establish a durable edge or deployment fitness.

## Promotion gates
Minimum research thresholds currently defined in the replay policy are 100 total closed trades, 30 OOS trades, all-sample PF >= 1.20, OOS PF >= 1.10, positive OOS net, plus native broker provenance, multi-regime coverage, cost validation and MT5 reproduction. Passing numeric thresholds alone is not sufficient.

## Current decision
NO STRATEGY QUALIFIED. DEMO ONLY. LIVE BLOCKED. Frozen V2.12 benchmark remains unchanged.
