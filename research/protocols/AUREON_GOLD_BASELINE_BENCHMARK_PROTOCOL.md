# AUREON Ω — Gold Baseline Benchmark Protocol
**Status:** Research specification; no strategy is approved.  
**Instrument:** XAUUSD first; BTC and other symbols excluded.  
**Execution:** DEMO-only research; LIVE remains BLOCKED.  
**Protected reference:** V2.12 remains frozen and must not be overwritten.

## Objective
Select a simple, reproducible benchmark and test whether advanced strategies add incremental edge after realistic costs. Do not select a winner by headline PF or in-sample net profit.

## Benchmark stack
1. **Accounting controls:** no-trade, buy-and-hold only where meaningful, and cost/round-trip sanity checks. These are diagnostic controls, not trading candidates.
2. **Simple trend baseline:** session VWAP direction plus EMA trend/pullback. Use only completed bars and causal features. Session VWAP reset and timezone must be explicitly configured and validated.
3. **Simple range baseline:** prior completed session/day high-low breakout with retest/acceptance rule. Use as the comparator for breakout strategies.
4. **Simple reversal baseline:** prior range sweep followed by close-back-inside confirmation, without MSS/FVG add-ons. Use as the comparator for CRT/liquidity-sweep strategies.
5. **Frozen historical control:** V2.12, reproduced from its exact original configuration and data where available. Never overwrite it; if inputs cannot be reproduced, label it reference-only.
6. **Advanced challengers:** FVG, AMD, MSS, news regime and cross-market filters. A challenger must beat its closest simple comparator, not just show positive returns.

## Data and execution requirements
- Keep third-party Dukascopy and PXBT-native data provenance distinct; never label one as the other.
- Prefer quote-level bid/ask replay for fills. OHLC-only tests must be labelled approximate and cannot qualify a strategy for promotion.
- Model spread, slippage, commission, swap where applicable, contract size, tick size/value, volume constraints, margin and account-currency conversion from verified instrument specifications.
- Use broker/session timezone mapping with DST handling; never assume 09:00 SAST equals a fixed UTC hour throughout all historical data without verifying source timestamps and intended session definition.
- Reject invalid/crossed/nonpositive quotes, duplicate timestamps, unsupported archive members, unexplained gaps and incomplete coverage. Publish row counts, coverage, gaps, spread quantiles and archive hashes.
- Define same-bar stop/target collision handling; prefer quote/tick ordering. If only OHLC exists, use conservative stop-first ordering and mark the result non-promotable.
- Signals may use only information available at the decision timestamp. Entries occur no earlier than the next tradable quote/bar after signal confirmation.

## Evaluation design
- Freeze the hypothesis and parameter grid before the test.
- Split chronologically into development, validation and untouched final holdout; do not repeatedly tune against the holdout.
- Add rolling/walk-forward checks and report results by year, session, volatility regime, long/short side and spread regime.
- Report net expectancy per trade, PF, trade count, win rate, max equity drawdown, average adverse/favourable excursion where available, exposure/time in market, costs, longest loss streak, and uncertainty intervals.
- Report all configurations attempted and apply a multiple-testing/selection-bias warning. Do not rank sparse OOS samples as winners.
- Compare every challenger to both its simple family baseline and a no-trade/cost sanity control on identical dates and assumptions.

## Provisional promotion gates
These are minimum research gates, not a guarantee of future profitability:
- Data provenance and execution model documented; no unresolved critical data-quality defects.
- At least 200 out-of-sample trades across the combined holdout/walk-forward periods, with sufficient coverage in each material regime; otherwise classify as insufficient evidence.
- Positive net expectancy after realistic costs; OOS PF > 1.10 as a screening threshold, not a stand-alone pass.
- No single month or small subset of trades contributes a majority of total net profit; report concentration.
- Robustness to modest parameter perturbations and increased spread/slippage; no catastrophic dependence on one session or side.
- Drawdown and risk metrics fit predeclared account-level limits; position sizing is normalized to risk, not arbitrary lot sizes.
- Independent reproduction and DEMO forward validation before any promotion. LIVE remains blocked unless separately authorized through the project's safety process.

## Required artifacts for each run
1. Versioned configuration and source commit SHA.
2. Dataset manifest: provenance, hashes, timestamps, timezone, valid rows, gaps, spreads.
3. Per-trade ledger with signal/entry/exit timestamps, bid/ask, costs, exit reason, R-multiple and equity curve.
4. Baseline-versus-challenger comparison table on the exact same samples.
5. Validation report with failures, limitations and explicit decision: REJECT / INSUFFICIENT EVIDENCE / DEMO FORWARD TEST.
6. Automated tests for causality, no look-ahead, order collision, cost calculations, timezone boundaries, duplicate events and risk limits.

## Immediate experiment order
A. Validate dataset and broker/session time assumptions.  
B. Build and test the simple VWAP/EMA baseline.  
C. Build simple range breakout/retest and sweep/reclaim controls.  
D. Replay all three with a shared quote-level execution engine.  
E. Compare the existing CRT variants against their simple reversal control.  
F. Only then add advanced filters and parameter searches.

## Current known limitations
The existing CRT sweep uses derived M5 bars from third-party Dukascopy history, not PXBT-native ticks, and its execution-cost model is approximate. Its results are exploratory only and must not be promoted. V2.12 metrics previously reported in project notes are historical claims until independently reproduced from their original settings and inputs.
