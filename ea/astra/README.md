# AUREON Ω — ASTRA Campaign EA V1

This branch is the deterministic MT5/MQL5 research implementation of the AUREON Ω ASTRA trade-campaign architecture.

## Scope

- Symbol focus: XAUUSD
- Execution timeframe: M5
- Context: M15 / H1 / H4
- Campaign entries: E1–E5
- Default fixed allocation: 0.10 lot maximum, 0.02 lot per tranche
- Alternative sizing: campaign-level percentage risk
- No martingale
- No grid
- Closed-candle confirmation by default
- Manual/web ASTRA intelligence is not required for the EA to run
- Strategy Tester research output is written to CSV

## Deterministic sequence

H4 context → H1 alignment → M15 liquidity sweep/reclaim → M5 MSS → displacement quality → FVG → retracement → E1 → qualified scale-ins → protection → TP1/TP2/TP3/runner.

## Build

The GitHub Actions workflow `.github/workflows/mt5-astra-compile.yml` downloads the official MT5 installer, runs MetaEditor under Wine, compiles the EA, and publishes compile evidence as an artifact.

The shared compile script accepts `EA_SOURCE`, allowing the original baseline EA to remain unchanged while this branch compiles the ASTRA implementation independently.

## Validation order

1. Compile with zero errors.
2. Frozen baseline backtest.
3. Verify trade/state logs and visual markers.
4. Parameter sensitivity tests.
5. Out-of-sample test.
6. Walk-forward analysis.
7. Monte Carlo / execution-stress analysis.
8. Only then consider forward-demo testing.

Do not optimize for headline win rate. Optimize for robust expectancy, drawdown control, repeatability, and execution realism.
