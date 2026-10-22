# AUREON Ω — Market-Context and Execution Audit
Date: 2026-10-21

## Executive finding

The corrected replay and dependency-corrected validation workflow both completed successfully. The accounting fix did not produce an approved strategy. The sample is only about 20 days, is third-party Dukascopy rather than verified PXBT broker-native data, and still uses M5 OHLC exits. Results are research diagnostics, not a claim of live profitability.

## Execution-cost timing defect fixed

- Added `spread_open` from the first quote in each M5 bar and use it for entry cost; the previous mean spread included quotes after the modeled entry.
- Added `spread_max` and use the maximum spread in the exit M5 bar as a conservative bound.
- Reject entry when the first quote spread at the next-bar entry exceeds 0.80 price units.
- Added regression coverage separating opening, mean and maximum spread.
- CI now installs pandas, NumPy and PyArrow before running the replay unit tests.

Validation:
- Corrected replay: [GitHub Actions run 39671685656](https://github.com/jerryllee421-lab/aureon-omega/actions/runs/39671685656) — success.
- Dependency-corrected validation: [GitHub Actions run 39671691045](https://github.com/jerryllee421-lab/aureon-omega/actions/runs/39671691045) — success.
- Tick archive SHA-256 verified: `d354c8769bd4d6f6c5a57a7da87843acdddec4f03815137b339c6ed5786069b0`.
- Replay artifact: `aureon-offline-tick-research`, run 39671685656.

## Corrected replay snapshot

Archive: 3,820,624 quotes, 3,816 derived M5 bars, 2026-10-01 through 2026-10-20 UTC. Chronological split: 2026-10-14 15:35 UTC. P/L is in price units, not account currency.

| Strategy | Trades | All-sample net | All-sample PF | OOS trades | OOS net | OOS PF |
|---|---:|---:|---:|---:|---:|---:|
| Daily CRT | 42 | +15.89 | 1.094 | 13 | -10.97 | 0.807 |
| AMD session | 28 | -38.97 | 0.723 | 12 | -3.88 | 0.931 |
| FVG scalper | 77 | -32.52 | 0.891 | 21 | -17.51 | 0.785 |
| Gold trap | 122 | -176.77 | 0.673 | 39 | -68.52 | 0.605 |
| H1 breakout | 29 | -128.12 | 0.287 | 9 | -20.81 | 0.485 |
| H4 breakout | 11 | -1.43 | 0.973 | 4 | -33.37 | 0.000 |
| Session breakout | 45 | -227.47 | 0.272 | 13 | -75.84 | 0.185 |
| Session VWAP + EMA | 119 | -278.10 | 0.514 | 35 | -110.08 | 0.382 |
| M5 mean reversion | 1 | +15.80 | N/A | 0 | 0.00 | N/A |
| Daily swing | 0 | N/A | N/A | 0 | N/A | N/A |

Daily CRT remains only a research hypothesis: its OOS net and PF are negative. Daily swing has no trades because the sample does not satisfy its completed-daily-bar requirement; it is untested, not disproven. M5 mean reversion has one trade and supports no inference.

## Why these results are still not deployment evidence

1. **Approximate exits:** stop/target order is inferred from M5 OHLC. When both levels fall within a candle, stop-first is conservative but does not reproduce actual quote chronology.
2. **Mid-price model:** the replay does not yet simulate executable bid/ask fills at each quote. Exit spread uses the entire exit bar's maximum as a bound, not the exact spread at exit time.
3. **Data provenance:** Dukascopy data is not verified against PXBTTrading-1 broker-native ticks.
4. **Sessions:** UTC labels are proxies; PXBT server time and DST boundaries are unverified.
5. **Broker economics:** commission, swap, contract size, tick value and ZAR conversion remain unverified.
6. **Regime attribution:** regime × session × setup × direction results with adequate independent trade counts have not been established.
7. **Coverage:** this is not a multi-regime, multi-year walk-forward test.

## Next engineering sequence

1. Build quote-level execution: signals only after a completed M5 bar; enter on the first eligible subsequent quote; buy at ask and sell at bid; evaluate SL/TP in timestamp order; apply explicit slippage and reject stale/gapped quotes.
2. Add deterministic unit tests for long/short entries, spread, SL/TP ordering, gaps, and end-of-data handling.
3. Freeze causal regime labels from completed bars only: volatility percentile, trend strength/slope, range-vs-expansion and session. Then report expectancy with counts and uncertainty; thin bins remain inconclusive.
4. Run longer anchored walk-forward evaluation with a locked final holdout and no holdout tuning.
5. Reproduce candidates in MT5 Strategy Tester using broker-native “Every Tick Based on Real Ticks” and verified PXBT costs.

## Release status

**NO STRATEGY APPROVED. DEMO ONLY. LIVE BLOCKED. Frozen V2.12 remains unchanged.**

This report records research-engineering progress, not a profitability claim.
