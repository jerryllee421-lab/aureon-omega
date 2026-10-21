# Walk-forward evaluation protocol

This evaluator measures the research predictor chronologically using a bounded
history at each forecast timestamp. It reports Brier score and log loss, a
historical-prior baseline, directional accuracy, coverage, per-regime metrics,
and a simple directional close-to-close PnL proxy after a flat cost assumption.

## Important interpretation
- Lower Brier score and log loss are better; compare to the baseline on identical
  forecast timestamps. Scores alone do not establish trade profitability.
- Coverage is the share of forecasts not rejected by the model's abstention gate.
- Directional accuracy is conditional on both the model and outcome being
  directional. Always report its sample count.
- Proxy PnL is not an MT5 backtest: it excludes intrabar stop/target path, bid/ask
  execution, commission schedule, swaps, slippage distribution, gaps, and partial
  fills. A zero PnL observation is not counted as a trade in the proxy summary.
- Forecasts are sampled at a fixed stride at least as large as the outcome
  horizon, avoiding overlap between adjacent outcome windows. Labels and model
  features use only information available at forecast time.

## Promotion gates (set before seeing holdout results)
1. Compare with the frozen V2.12 control on identical data and realistic costs.
2. Report calibration, confidence intervals, coverage, trades, net expectancy,
   drawdown, profit factor, regime/session/direction slices and all cost assumptions.
3. Run rolling walk-forward folds and reserve an untouched final holdout.
4. Stress costs and delayed entries; reject edges that disappear under modest
   perturbations or rely on one short period.
5. Confirm in native MT5 real-tick testing, then DEMO forward test and reconcile
   every signal to broker deal history before considering any promotion.
6. No automatic live trading or self-modifying production rules.
