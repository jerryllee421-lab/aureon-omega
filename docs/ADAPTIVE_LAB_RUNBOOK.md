# AUREON Adaptive Lab — Local Historical Evaluation

This runner discovers canonical XAUUSD Parquet partitions beneath the local AUREON root, selects a bounded timeframe group (M5 preferred, then M15/M30/H1/M1/H4/D1), stages selected columns into a temporary Parquet file, and produces walk-forward and cost-sensitivity reports. It does not connect to MT5 or place trades.

## Memory-safe starting point

On an 8 GB Windows machine, start with canonical M5 or M15 bars. The default loader caps input at 1,200,000 rows and reads only timestamps plus high/low/close. It rejects duplicate timestamps, invalid OHLC geometry, missing prices, and datasets above the cap before converting bars to Python objects. Raise the cap only after checking available RAM.

One-click run on the existing local master dataset (no MT5 terminal required):

~~~bat
scripts\\run_adaptive_lab.cmd "C:\\Users\\User\\Desktop\\AUREON"
~~~

Or run the discovery wrapper directly from the repository root:

~~~powershell
python -m research.evolution.run_local_gold_dataset --data "C:\\Users\\User\\Desktop\\AUREON" --out research_results/adaptive_lab --side bid --timeframe auto --max-rows 1200000 --horizon 5 --stride 60 --lookback 1500 --cost-bps 8 --cost-grid-bps 4,8,12,20
~~~

The wrapper selects one canonical timeframe partition root, checks Parquet row counts against the cap before staging, hashes each selected source file, and records the actual date coverage in the report. If selected M5 history is not ten years, the report will expose the shorter range; do not describe it as a full-decade result unless the timestamps confirm that.

## Outputs

- adaptive_lab_report.json: source SHA-256, data range, parameters, walk-forward metrics, cost scenarios, and explicit execution authority flags.
- Console summary: forecast count, coverage, Brier score vs. a rolling-prior baseline, and close-to-close PnL proxy.

## Interpretation and release gates

- Lower Brier/log loss than the prior baseline is evidence of improved probabilistic forecasts, not proof of a tradable edge.
- Cost scenarios use flat basis-point floors, not actual PXBT spread/slippage/fill modelling.
- The PnL series is a close-to-close directional proxy; it does not model bid/ask entry/exit, stop/target ordering, latency, commissions, swaps, or market impact.
- Do not promote a candidate from these metrics alone. Require a frozen V2.12 control comparison on identical dates, untouched holdout, parameter-neighbourhood tests, and native MT5 Every Tick Based on Real Ticks validation.
- Reports are research-only, execution_authorized=false, and explicitly retain the live-trading block.
