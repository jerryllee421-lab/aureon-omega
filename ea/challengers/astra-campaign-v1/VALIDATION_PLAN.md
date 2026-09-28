# ASTRA Gold Campaign V1 — validation gates

## Frozen baseline
The file `ASTRA_GOLD_V1_BASELINE.set` is the canonical V1 baseline. Do not tune it before the baseline report is captured and archived.

## Gate 1 — compiler
- Official MetaEditor compiler
- 0 errors
- 0 warnings
- EX5 hash recorded

## Gate 2 — native Strategy Tester baseline
- XAUUSD M5
- Every tick based on real ticks (Model=4)
- M15/H1/H4 context loaded by EA
- Deposit USD 10,000
- Leverage 1:100
- Local agent only
- No cloud optimization
- Five-year target range where broker real-tick history is actually available
- Preserve report, tester logs, CSV evidence, EA hash and SET hash

If the broker cannot supply the requested real-tick range, the run must be marked DATA_INCOMPLETE rather than silently falling back to generated ticks.

## Gate 3 — logic audit
Verify a sample of campaigns candle-by-candle:
sweep → reclaim → H4/H1 alignment → M5 MSS → displacement → FVG → E1 → E2-E5 qualification → SL/TP/partial/runner.

## Gate 4 — controlled comparisons
Run the exact same data window with:
- E1 only
- E1-E3
- E1-E5
- protected-adds on/off
- smart protection on/off

No parameter optimization yet.

## Gate 5 — robustness
Only after the frozen baseline:
- out-of-sample
- walk-forward
- spread/slippage stress
- delayed execution
- Monte Carlo trade-order resampling
- broker-data comparison

## Acceptance
Prefer robust positive expectancy and controlled drawdown over headline win rate. Reject any configuration whose performance depends on a narrow parameter value, a single month, or unrealistic execution assumptions.
