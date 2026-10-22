# AUREON Ω — 09:00 SAST Daily CRT Research Results

**Run:** [Full-history CRT sweep](https://github.com/jerryllee421-lab/aureon-omega/actions/runs/39678624119)  
**Artifact:** `aureon-full-history-crt-research` (JSON results + trade ledger)  
**Research branch:** `research/market-context-execution-audit-20261021`  
**Dataset provenance:** third-party Dukascopy; **not PXBT-native ticks**.  
**Status:** exploratory only; no candidate approved; DEMO-only; LIVE BLOCKED.

## Completed sweep

- Published monthly ZIP archives downloaded and size-checked.
- 141,535 derived M5 bars processed.
- 48 combinations tested: 2 range definitions × 4 confirmation rules × 3 targets (1.5R/2R/3R) × 2 stop buffers (0/0.1 ATR).
- Chronological split: 70% train / 30% OOS; split timestamp `2026-03-16T13:35:00+00:00`.
- All 48 variants remained blocked by the exploratory evidence gates.

## Findings

The best all-sample result by net price units was **pre-session range + displacement/FVG confirmation + 1.5R target + 0.1 ATR stop buffer**:

| Metric | All sample | OOS |
|---|---:|---:|
| Trades | 11 | 3 |
| Net price units | +12.0417 | +17.9297 |
| Profit factor | 1.4068 | 3.6764 |
| Win rate | 54.55% | 66.67% |
| Maximum drawdown, price units | 15.9412 | 0.0000 |

This is **not a validated winner**: only 11 trades overall and 3 OOS trades. The OOS PF is statistically fragile and is not enough to justify deployment.

Among higher-frequency variants, none was profitable OOS. For example, pre-session range + displacement + 1.5R target (no ATR buffer) produced 141 trades overall, net -132.2885 price units, PF 0.6893; OOS was 47 trades, net -16.1435, PF 0.9100. The basic pre-session reclaim 1.5R variant generated 324 trades overall and lost -498.7965 price units (PF 0.4837); OOS lost -211.3875 (PF 0.5286).

## Execution and data limitations

- The replay uses derived M5 OHLC candles, **not quote-by-quote fill simulation**.
- Stop is assumed first when stop and target are both touched within one M5 bar.
- Entry is next-bar open; spread cost uses entry spread and maximum spread in the exit bar; slippage is fixed at 0.70 price units round trip.
- Commission, swap, contract sizing, account-currency conversion, and PXBT-specific execution behavior are not modelled.
- 09:00 SAST is assumed to be 07:00 UTC. Historical timezone and broker-server-time alignment must be verified.
- The current parameter sweep does not establish that the pattern survives PXBT-native tick execution or broader independent holdout periods.

## Decision and next actions

1. Do not promote any CRT variant to candidate/production status from this result.
2. Keep V2.12 frozen and unchanged.
3. Run quote-quality coverage checks and add their results to the next artifact; parse errors or unsupported members must be reported explicitly.
4. Improve the fill model with bid/ask quote-level entry and stop/target handling, then rerun the top few hypotheses on PXBT-native ticks when available.
5. Require substantially more OOS trades, positive net after realistic costs, stable performance across periods, and risk checks before any DEMO forward test. LIVE remains blocked.
