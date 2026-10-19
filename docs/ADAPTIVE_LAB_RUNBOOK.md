# AUREON Adaptive Lab — Local Historical Evaluation

This runner evaluates the adaptive prediction engine against a canonical XAUUSD parquet file. It produces a walk-forward probability report and a cost-sensitivity report; it does not place trades.

## Memory-safe starting point

On an 8 GB Windows machine, start with canonical M5 or M15 bars. The default loader caps input at 1,200,000 rows and reads only timestamps plus high/low/close. It rejects duplicate timestamps, invalid OHLC geometry, missing prices, and datasets above the cap before converting bars to Python objects. Raise the cap only after checking available RAM.

Example from the repository root:

~~~powershell
python research/evolution/run_adaptive_lab.py --data research_data/XAUUSD/canonical/XAUUSD_M5.parquet --out research_results/adaptive_lab --side bid --horizon 5 --stride 60 --lookback 1500 --cost-bps 8 --cost-grid-bps 4,8,12,20
~~~

For a local ten-year file, supply its actual path to --data. The filename above is an example and must exist locally. If the file is M1 and exceeds the default cap, resample/validate it to M5 or M15 first rather than loading all ten years into memory.

## Outputs

- adaptive_lab_report.json: source SHA-256, data range, parameters, walk-forward metrics, cost scenarios, and explicit execution authority flags.
- Console summary: forecast count, coverage, Brier score vs. a rolling-prior baseline, and close-to-close PnL proxy.

## Interpretation and release gates

- Lower Brier/log loss than the prior baseline is evidence of improved probabilistic forecasts, not proof of a tradable edge.
- Cost scenarios use flat basis-point floors, not actual PXBT spread/slippage/fill modelling.
- The PnL series is a close-to-close directional proxy; it does not model bid/ask entry/exit, stop/target ordering, latency, commissions, swaps, or market impact.
- Do not promote a candidate from these metrics alone. Require a frozen V2.12 control comparison on identical dates, untouched holdout, parameter-neighbourhood tests, and native MT5 Every Tick Based on Real Ticks validation.
- Reports are research-only, execution_authorized=false, and explicitly retain the live-trading block.
