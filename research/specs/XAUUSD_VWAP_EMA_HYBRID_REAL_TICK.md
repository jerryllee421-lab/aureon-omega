# AUREON Ω — XAUUSD VWAP + EMA Hybrid Real-Tick Research Spec

Status: **RESEARCH CONFIGURED — NOT DEPLOYMENT-APPROVED**
Created: 2026-10-20
Branch: `research/xauusd-vwap-ema-hybrid-20261020`

## Mandate and safety boundary

- Instrument: broker-native XAUUSD; record broker/server, symbol specification, digits, tick size/value, contract size, trading sessions, and account currency with every run.
- Mode: offline research and MT5 Strategy Tester / DEMO-only forward validation.
- Live trading: hard-blocked. This strategy specification does not grant broker execution authority and must not enable live order placement.
- Frozen control: preserve V2.12 Champion artifacts and reports byte-for-byte. Never overwrite or retune the frozen benchmark.
- Promotion: no strategy is approved on backtest profit alone. Require reproducible real-tick evidence, realistic costs, drawdown controls, and DEMO forward validation.

## Locked initial configuration

| Setting | Value |
|---|---|
| Entry style | Hybrid trend-filter + pullback/reclaim |
| Signal timeframe | M1 |
| Trend confirmation | M5, closed candles only |
| VWAP | Session VWAP; reset at configured broker-session boundary |
| EMA fast / trigger | EMA 9 |
| EMA confirmation | EMA 21 |
| Trend filter | EMA 50 |
| Macro context | EMA 200, informational/filter only; evaluate ablation |
| Signal evaluation | On completed M1 candle; no intrabar look-ahead |
| Entry execution model | Tick-by-tick bid/ask, spread and slippage applied |
| Initial position sizing | Fixed minimal DEMO lot; derive permitted volume from broker symbol constraints |
| Re-entry / pyramiding | Disabled for first baseline |
| Benchmark | Frozen V2.12, immutable control |
| Deployment | Not approved |

## Indicator definitions

1. EMA values are computed from chronological broker M1/M5 bars using the close price. A signal uses only bars closed before the decision timestamp.
2. Session VWAP is computed as cumulative typical-price × tick-volume divided by cumulative tick-volume, using the broker's available real-tick-derived bar tick volume and a documented session start/reset. This is a **tick-volume proxy**, not centralized spot-gold traded volume.
3. Do not mix time zones or reset VWAP silently. Store the broker-server session boundary and timezone in run metadata. Exclude or explicitly label incomplete session-start warm-up.
4. Real-tick execution must use actual historical bid/ask where available. Never synthesize missing ticks and label them real ticks. Report coverage gaps and quality separately.

## Candidate signal rules (initial hypothesis; validate, do not assume edge)

### Long candidate

- M5 close is above session VWAP and M5 EMA21 > EMA50; EMA200 is logged as context.
- M1 EMA9 > EMA21, or a pullback/reclaim setup is forming without using an unfinished candle.
- Price has pulled back toward M1 EMA21 or session VWAP and the completed M1 candle confirms a bullish reclaim.
- Current spread, tick freshness, market session, stop distance, and risk limits all pass.
- Enter at the first eligible tick after the completed signal, using executable ask and a recorded latency/slippage model.

### Short candidate

- M5 close is below session VWAP and M5 EMA21 < EMA50.
- M1 EMA9 < EMA21, or a pullback/rejection setup is forming without using an unfinished candle.
- Price has retraced toward M1 EMA21 or session VWAP and the completed M1 candle confirms bearish rejection.
- Current spread, tick freshness, market session, stop distance, and risk limits all pass.
- Enter at the first eligible tick after the completed signal, using executable bid and a recorded latency/slippage model.

### No-trade conditions

- M5 direction and VWAP location conflict, or M1 trigger is absent.
- Market closed, stale/invalid ticks, malformed chronology, missing bid/ask, or symbol specification mismatch.
- Spread or estimated all-in transaction cost exceeds the configured threshold.
- Risk cap, daily loss cap, maximum drawdown guard, or margin guard would be breached.
- Signal depends on future data, incomplete bars, or a VWAP session reset that cannot be established.
- On any uncertain state, fail closed and log the reason.

## Risk and cost model

- First research baseline: one position at a time, no averaging down, no grid, no pyramiding, and no automatic lot escalation after a loss.
- Size only after SL distance and broker tick-value/tick-size conversion are verified. Risk per trade must be configurable and bounded by a conservative research ceiling; daily loss and equity drawdown circuit breakers must be tested.
- Include spread, commission, swap/financing where applicable, slippage, latency, rejected orders, partial fills, and broker stop/freeze levels. Where a cost cannot be evidenced, disclose it as missing and do not treat results as deployment-grade.
- Report gross and net P&L separately; profit factor, expectancy, trade count, win rate, average win/loss, MAE/MFE, exposure, turnover, and maximum equity/balance drawdown. Define profit factor on net trade P&L and state treatment of zero/negative denominators.
- Compare cost sensitivity scenarios, including base measured costs and adverse spread/slippage stress. Do not optimize thresholds on the final holdout.

## Required validation sequence

1. **Data integrity:** verify real-tick source, symbol, timezone, chronological ordering, duplicates, gaps, bid/ask validity, spread distribution, tick coverage and date range. Record checksums and immutable input manifest.
2. **Parity:** compare indicator values and signal timestamps against an independent implementation on selected hand-checked windows.
3. **Baseline:** run the candidate with Every tick based on real ticks in MT5 Strategy Tester where available. Use identical dates, symbol settings and costs for comparable control/candidate runs.
4. **Temporal splits:** train/calibrate only on development data; evaluate on a later validation segment and untouched holdout. No random row split for time-series trading.
5. **Ablations:** test VWAP-only, EMA-only, VWAP+EMA, M5 filter on/off, EMA200 filter on/off, and pullback/reclaim variants. Change one factor at a time.
6. **Robustness:** segment by session, volatility regime, spread decile, long/short, month and year; report concentration of profits and failure modes.
7. **Risk gates:** reject if net expectancy is non-positive on holdout, drawdown exceeds the pre-registered ceiling, results collapse under modest adverse costs, or results depend on a small number of outlier trades. Pre-register numeric thresholds before reading holdout outcomes.
8. **DEMO forward:** only after offline gates pass, run on PXBTTrading-1 DEMO with LIVE blocked. Log each signal, rejection, quote, order request/result, fill, cost, exit, and equity/risk state. Do not infer success from a short sample.
9. **Promotion review:** candidate remains research-only until all artifacts and gates are reviewed. Never modify V2.12 to make the challenger appear better.

## Evidence artifacts required per run

- Git commit, strategy/config hash, tester build, broker/server, symbol specification, data manifest/checksum, date range, modelling mode and tick-quality report.
- Exact parameter set, session reset timezone, cost assumptions, rejected-signal reasons and trade-level ledger.
- Machine-readable metrics plus tester HTML/report and logs.
- Comparison against immutable V2.12 control, with differences and confidence limitations.
- Final disposition: PASS / FAIL / INCONCLUSIVE, with failed gates listed.

## Current implementation status

This commit establishes the research specification only. It does **not** claim that an EA has been compiled, that a real-tick backtest has run, that the repository contains the required raw tick archive, or that profitability has been established. Native MT5 compilation, Strategy Tester execution, and DEMO forward evidence require verified access to the relevant MT5 environment and datasets.
