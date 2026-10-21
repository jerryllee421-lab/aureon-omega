# AUREON Ω — XAUUSD Research Diagnostic (2026-10-21)

## Decision

**NO STRATEGY APPROVED. DEMO ONLY. LIVE BLOCKED.** This is a short exploratory offline replay, not a broker-native MT5 backtest. The January 2025 recovery is not a blocker for this separate October 2026 archive replay.

## Evidence inspected

- Published archive: `xauusd-ticks-2026-10.zip`
- SHA-256: `d354c8769bd4d6f6c5a57a7da87843acdddec4f03815137b339c6ed5786069b0` (verified by CI).
- Coverage: 2026-10-01 00:00:00.017 UTC to 2026-10-20 18:59:59.821 UTC.
- 3,820,624 quote rows; 17 Parquet members; 3,816 derived M5 bars.
- Provenance is third-party Dukascopy, **not verified PXBTTrading-1 native ticks**.
- Negative spreads, exact duplicate quotes and zero spreads reported: 0 each.
- Spread median 0.545, p95 0.75, max 12.564 price units.
- Largest time gap 176,459.533 seconds; likely a market closure/weekend gap, but the earlier report did not classify gaps by weekday/closure. The refreshed audit adds that classification and spread-threshold counts.
- The replay assumes mid-price fills, a spread cost on entry/exit and 0.35 price units of slippage per side; commission is set to zero. Contract sizing, ZAR conversion, swap and actual broker execution are not modelled.
- M5 OHLC is synthesized from quote ticks. The report cannot validate intrabar execution sequencing or replace MT5's native “Every tick based on real ticks” model.

## Strategy results (before any additional cost-stress multiplier)

| Strategy | Trades | Net price units | PF | OOS trades | OOS net | OOS PF |
|---|---:|---:|---:|---:|---:|---:|
| M5 mean reversion | 1 | +15.27 | N/A | 0 | 0.00 | N/A |
| H4 breakout | 11 | -5.60 | 0.90 | 4 | -34.44 | 0.00 |
| Session breakout | 45 | -245.57 | 0.25 | 13 | -81.63 | 0.17 |
| Daily CRT | 43 | +18.99 | 1.11 | 13 | -16.86 | 0.72 |
| Session VWAP + EMA | 119 | -292.87 | 0.50 | 35 | -122.43 | 0.35 |

The split is chronological, at 70% of the derived M5 bar series. No candidate passes the minimum trade count, OOS PF/net, provenance, multi-regime, cost stress, walk-forward and native MT5 gates.

## Diagnosis

1. **Sample too short.** Roughly 20 calendar days is not enough to establish durable edge. Even the one positive mean-reversion trade is statistically meaningless.
2. **Daily CRT degrades out of sample.** PF falls from 1.33 in sample to 0.72 OOS; the in-sample edge does not persist.
3. **Session breakout and VWAP+EMA are materially negative after modeled costs.** Do not promote or optimize these against this sample as if they were proven winners.
4. **H4 breakout reverses OOS.** Four OOS trades are too few for a definitive rejection, but the evidence is currently adverse.
5. **Cost realism remains incomplete.** Commission is zero; swap and account-currency conversion are absent. Current cost assumptions are illustrative and need PXBT contract specifications.
6. **Quote quality needs closure-aware diagnostics.** A max-gap statistic alone is misleading across weekends/market closures. The refreshed script reports long-gap counts, weekday gaps under 24 hours, and quote spreads above the configured threshold.
7. **Replay is not MT5 certification.** Stops/targets are evaluated against synthetic M5 OHLC; a real tick can hit both stop and target in sequence. This replay uses conservative stop-first ordering, but it is still not the terminal's native tick engine.
8. **No fresh live-market evidence.** A compile is a code-quality gate, not a profitability test. No orders were placed.

## Engineering updates

- Added same-signal cost sensitivity at 1.0x / 1.5x / 2.0x modeled transaction costs. This isolates how the current trade ledger degrades under higher costs; it does not simulate altered fills.
- Added spread threshold counts and gap diagnostics to the offline replay report.
- Removed nonfunctional orchestration marker comments from the EA and replay source.
- Triggered CI, offline replay and MT5 compile workflows on the research branch; final results must be checked after those runs complete.

## Next gates

1. Review refreshed audit/replay output and confirm cost-stress metrics are present and internally consistent.
2. Fix strategy logic or reject candidates based on repeatable, out-of-sample evidence—not parameter fishing on this short sample.
3. Extend evaluation to multiple market regimes with anchored walk-forward folds and locked holdout dates.
4. Obtain broker-specific symbol specs, commission/swap and tick-size/value details.
5. Reproduce the shortlisted candidate in MT5 Strategy Tester with **Every Tick Based on Real Ticks**, DEMO configuration and the same date range.
6. Preserve frozen V2.12 unchanged as the control. No LIVE enablement.


## Refreshed cost-stress findings

The refreshed workflow completed successfully at [run 39668917410](https://github.com/jerryllee421-lab/aureon-omega/actions/runs/39668917410). The additional audit reports 124,917 quotes with spread above 0.80 and 3,244 above 2.00 price units; the maximum spread is 12.564. There are 13 gaps longer than 60 seconds and the largest weekday gap below 24 hours is 3,606.1 seconds. Gap classification is a diagnostic only; those long gaps still need timestamp-level inspection before treating them as outages rather than source/session behavior.

Cost stress on the **same fixed trade decisions**:

| Strategy | 1.0× net | 1.5× net | 2.0× net | PF at 2.0× |
|---|---:|---:|---:|---:|
| Daily CRT | +18.99 | -21.05 | -61.09 | 0.71 |
| H4 breakout | -5.60 | -15.34 | -25.08 | 0.63 |
| Session breakout | -245.57 | -285.44 | -325.31 | 0.16 |
| Session VWAP + EMA | -292.87 | -402.57 | -512.26 | 0.29 |
| M5 mean reversion | +15.27 | +14.28 | +13.28 | N/A (one trade) |

**Interpretation:** Daily CRT's small positive full-sample net disappears at 1.5× modeled costs, while the two negative strategies deteriorate further. The one-trade mean-reversion result is not evidence of robustness. This stress test multiplies recorded cost estimates without changing fill prices, signals, spread filters, or stop/target sequencing; it is a sensitivity check, not a full execution-cost simulation.


## Next-level model correction (2026-10-21)

Code review found that the prior replay charged the full entry spread plus the full exit spread while using mid-price P/L. The replay now charges half the entry spread plus half the exit spread, then adds two-sided slippage (0.35 price units per side). This changes the cost model; the earlier P/L/PF and cost-stress tables are historical diagnostics and should not be treated as the current ranking after the refreshed run.

The replay now also emits three equal-duration chronological stability folds with fixed parameters, trade count, net and PF. These are diagnostics, not independently optimized walk-forward models. The short sample may leave folds underpowered. Review the refreshed artifact before drawing updated conclusions.

Approval remains blocked until the refreshed report is checked, cost assumptions are validated against PXBT symbol economics, and native MT5 real-tick testing is complete.


## Corrected replay results (run 39669297901, 2026-10-21)

The corrected replay completed successfully and verified the archive SHA-256. These results supersede the earlier strategy and cost-stress tables above because the spread accounting changed.

| Strategy | Trades | Net price units | PF | OOS trades | OOS net | OOS PF | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Daily CRT | 43 | +43.97 | 1.28 | 13 | -10.13 | 0.82 | Research only; OOS negative |
| H4 breakout | 11 | +0.29 | 1.01 | 4 | -32.31 | 0.00 | Research only; OOS adverse, tiny sample |
| M5 mean reversion | 1 | +15.92 | N/A | 0 | 0.00 | N/A | No conclusion; one trade only |
| Session breakout | 45 | -221.45 | 0.28 | 13 | -75.09 | 0.19 | Reject current formulation for this sample |
| Session VWAP + EMA | 119 | -224.83 | 0.59 | 35 | -103.96 | 0.41 | Reject current formulation for this sample |

### Three chronological fixed-parameter folds

Daily CRT net results were +38.78 (PF 1.69; 16 trades), +21.94 (PF 1.70; 11 trades), then -16.75 (PF 0.76; 16 trades). The third period reversed the apparent positive edge. This is a stability warning, not proof of a permanent failure.

Session breakout was negative in all three folds: -90.72 (PF 0.28), -19.39 (PF 0.52), and -111.34 (PF 0.23). Session VWAP + EMA was negative in all three: -103.73 (PF 0.46), -61.12 (PF 0.65), and -59.98 (PF 0.66). H4 breakout and M5 mean reversion have too few trades for fold-level inference.

### Corrected cost sensitivity (same trade decisions)

| Strategy | 1.0× net | 1.5× net | 2.0× net | PF at 2.0× |
|---|---:|---:|---:|---:|
| Daily CRT | +43.97 | +16.43 | -11.11 | 0.94 |
| H4 breakout | +0.29 | -6.50 | -13.30 | 0.78 |
| Session breakout | -221.45 | -249.26 | -277.07 | 0.21 |
| Session VWAP + EMA | -224.83 | -300.50 | -376.17 | 0.41 |
| M5 mean reversion | +15.92 | +15.25 | +14.57 | N/A (one trade) |

### Engineering decision

- **No candidate qualifies.** All strategies fail one or more sample-size, out-of-sample, provenance, cost, and/or native-MT5 requirements.
- Daily CRT is the only candidate with positive full-sample net and PF above 1.2, but its 13-trade OOS segment is negative and its latest chronological fold is negative. Do not optimize it on this same holdout; preserve it as a research hypothesis and test it on new data.
- Session breakout and VWAP + EMA are consistently negative across folds; stop parameter-chasing this short sample. Any redesign must be treated as a new version and evaluated on a fresh holdout.
- The offline replay CI succeeded: [run 39669297901](https://github.com/jerryllee421-lab/aureon-omega/actions/runs/39669297901). The validation workflow's run was cancelled by concurrency after npm test, npm build and Python syntax checks had each completed successfully; do not count that run as a completed overall CI pass.
- Archive remains third-party Dukascopy, not verified PXBT-native ticks. Native MT5 “Every Tick Based on Real Ticks” testing and verified contract costs remain mandatory.

**Status unchanged: DEMO ONLY; LIVE BLOCKED; frozen V2.12 untouched.**
