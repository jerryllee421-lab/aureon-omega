# XAUUSD Real-Tick Replay — Diagnosis (2026-10-21)

## Status

- Replay workflow: PASS (GitHub Actions run 39642648213).
- Artifact: `aureon-vwap-ema-tick-replay`.
- Input: 3,820,624 third-party Dukascopy XAUUSD bid/ask ticks, 2026-10-01 through 2026-10-20 UTC.
- Coverage: 19,080 observed minutes; data ends at 2026-10-20 18:59:59 UTC. This is not a complete final UTC day.
- Feed authority: external Dukascopy, not PXBTTrading-1 native ticks.
- Test authority: Python tick-replay proxy, not MT5 Strategy Tester.

## Observed VWAP + EMA hybrid results

| Scenario | Trades | Win rate | Net R | Profit factor | Max drawdown (R) |
|---|---:|---:|---:|---:|---:|
| Spread cap 0.60 price units, no added slippage/commission | 229 | 31.00% | -51.50 | 0.730 | -53.50 |
| Spread cap 0.70, no added slippage/commission | 276 | 28.99% | -76.00 | 0.679 | -77.00 |
| Spread cap 0.85, no added slippage/commission | 296 | 27.70% | -91.00 | 0.633 | -91.50 |
| Spread cap 0.70, 0.01 slippage per side | 274 | 28.83% | -77.73 | 0.672 | -78.71 |
| Spread cap 0.70, 0.02 slippage per side | 275 | 28.73% | -79.97 | 0.665 | -80.93 |
| Spread cap 0.70, 0.01 slippage per side + 0.02 round-turn commission | 274 | 28.83% | -80.19 | 0.663 | -81.14 |

At the 0.70 cap, the baseline has 196 stop-loss exits (-196R before costs) and 80 take-profit exits (+120R before costs), for -76R net. Long trades contributed -50.5R across 123 trades; shorts contributed -25.5R across 153 trades. Wider spread allowance increases trade count and worsens the result in this sample.

## Diagnosis

1. **Candidate fails this preliminary sample.** Do not optimize it against these same dates or promote it. The result is a rejection of the current configuration on this sample, not proof that every VWAP/EMA design fails.
2. **Cost filtering matters, but does not rescue the strategy.** The tighter spread cap loses less, yet still has PF below 1 and negative net R.
3. **This is not a broker-cost-calibrated result.** Spread caps, slippage, and commission are stated in raw gold price units because broker point size, contract value and actual commission schedule are not confirmed.
4. **The test is not a proper holdout.** The entire short archive was replayed as one evaluation. No strategy parameters may be selected using these outcomes and then reported as out-of-sample.
5. **Session VWAP and bar construction are approximations.** UTC-day reset and tick-count volume are proxies; M1 bid bars and Python EMA/ATR semantics may differ from broker MT5 bars/indicators.
6. **The dataset has incomplete daily coverage at the end.** Do not interpret the 20-day archive as 20 complete trading sessions; the final day ends at 18:59:59 UTC.
7. **Native execution validation remains absent.** There is no broker-native MT5 Every Tick Based on Real Ticks report, contract-specification validation, or DEMO forward reconciliation from this replay.

## Required upgrades before rerunning

- Keep this run frozen as the initial negative baseline; preserve its report and trade ledger.
- Add the replay module to CI syntax validation (so future edits are checked).
- Add explicit input coverage/gap checks and report per-day tick counts, first/last timestamps, missing-minute gaps, and session completeness.
- Add a chronology-based 60/20/20 development/validation/untouched-holdout harness. Tune only on development; select using validation; run the holdout once.
- Compare the VWAP/EMA candidate against EMA pullback, liquidity-sweep/structure-shift, session breakout/retest, and range mean-reversion candidates under identical tick windows, cost assumptions, and risk definitions.
- Report long/short, session, volatility-regime and month-level breakdowns; add parameter-neighbourhood checks and a random-entry/shuffled-signal control.
- Calibrate spread, slippage, commission, symbol digits/point size, contract value and broker server session from PXBTTrading-1 DEMO data before interpreting results as broker-equivalent.
- Require native MT5 Strategy Tester **Every Tick Based on Real Ticks**, identical-date frozen V2.12 control comparison, untouched holdout, and DEMO forward reconciliation before any promotion.

## Safety

Research only. PXBTTrading-1 DEMO remains the permitted execution lane. Live trading remains blocked. Frozen V2.12 benchmark is not modified.
