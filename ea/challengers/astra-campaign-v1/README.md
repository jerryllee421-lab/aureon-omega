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


## Native MT5 Strategy Tester account context

The official MT5 terminal requires an active trading-account context before its Strategy Tester will start, even when the test symbol itself is a locally imported custom symbol.

For CI, use a **demo account only** and configure these GitHub Actions repository secrets:

- `MT5_DEMO_LOGIN`
- `MT5_DEMO_PASSWORD`

The demo server is pinned in the workflow as `PXBTTrading-1`; it is not a secret.

The Windows smoke workflow consumes these values only at runtime. They are not committed, printed, or copied into uploaded artifacts. A redacted tester configuration is retained for auditability.

Path in GitHub: **Repository → Settings → Secrets and variables → Actions → New repository secret**.

Do not use a live funded account for CI/backtesting credentials.

### Current native validation status

The Windows lane has independently proven:

1. Official MT5 installs on the GitHub-hosted Windows runner.
2. `AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5` compiles with MetaEditor at zero errors and zero warnings.
3. `AUREON_CustomSymbolLoader.mq5` compiles at zero errors and zero warnings.
4. The pinned external XAUUSD M1 dataset is imported into `ASTRA_XAUUSD` successfully.
5. The remaining native tester gate is authenticated demo-account context.

Once the two secrets exist, the smoke workflow can proceed through the actual Strategy Tester report generation before any long-range optimization is allowed.
