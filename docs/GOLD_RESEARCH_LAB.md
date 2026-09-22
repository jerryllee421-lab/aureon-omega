# AUREON Ω — Gold Research Lab

This module turns GitHub Actions into a mobile-controlled XAUUSD research worker.

## Data truth

- Research source: `DUKASCOPY_EXTERNAL` public XAUUSD bid/ask history.
- Raw source and derived data are never labelled broker-native.
- M1 is decoded from Dukascopy BI5 daily candle files, then all 21 standard MT5 timeframes are derived deterministically.
- Every generated timeframe is validated and SHA-256 hashed.
- No synthetic candles are generated to fill missing market data.
- Failed downloads fail the workflow rather than silently filling gaps.

## Strategy truth

`ea/baseline/FVG_Scalper_V2_11_ORIGINAL.mq5` is the immutable uploaded baseline.

The Python evaluator mirrors its structural FVG logic but uses a conservative bar-close execution proxy. It is **not** represented as tick-for-tick MT5 equivalence. Candidate strategies must eventually survive a native MT5 Strategy Tester verification on real ticks.

## Mobile use

From the GitHub mobile/web interface open **Actions → AUREON Gold Research → Run workflow**. Choose 1–5 years, M1/M5/M15/H1/H4 and a candidate budget. The workflow downloads data, validates it, runs development/validation/holdout research, performs Monte Carlo on finalists and produces a downloadable artifact.

## Research governance

Chronological split: 60% development / 20% validation / 20% untouched holdout. Parameter candidates are selected only on development data. Holdout performance is recorded after selection. Results are measured in R to avoid inventing broker-specific contract sizing.

Final EA promotion requires agreement between the Linux research result and a later MT5 real-tick test.
