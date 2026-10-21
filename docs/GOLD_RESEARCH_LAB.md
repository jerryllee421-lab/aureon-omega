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


## XAUUSD real-tick strategy test queue

All candidates below use the same chronological data splits, tick source, fill model, risk budget, and cost scenarios. The current archive is third-party Dukascopy bid/ask data, not PXBTTrading-1 broker-native history. A positive replay result is provisional until native MT5 Strategy Tester verification and demo forward reconciliation.

Priority order:

1. **Session VWAP + EMA hybrid** — existing active candidate; M1 signal/entry with completed M5 trend confirmation, ATR-based exits. Replay implementation: `research/replay/aureon_vwap_ema_tick_replay.py`.
2. **EMA trend continuation / pullback** — EMA 9/21/50 alignment, pullback and continuation confirmation; test M5 entries with M15/H1 regime filters.
3. **Liquidity sweep + structure shift** — prior-session or swing high/low sweep, reclaim, then confirmed BOS/CHoCH-style shift; no entry on sweep alone.
4. **Session range breakout + retest** — Asian/early-session range break and retest; filter by range size, spread, volatility and scheduled high-impact news windows where reliable timestamps exist.
5. **Range mean reversion** — VWAP/band extension with reversal confirmation; disable when trend/volatility regime indicates breakout conditions.

### Required comparison protocol

- Run each strategy independently before testing combinations; keep the frozen V2.12 control unchanged.
- Use development/validation/untouched holdout in chronological order (60%/20%/20%); no tuning on holdout.
- Model bid/ask fills and intrabar stop/target ordering from ticks. Apply the same spread filters and test at least 1.0x, 1.5x and 2.0x observed costs, plus explicit slippage and commission scenarios.
- Record trade count, net expectancy per trade in R, profit factor, max drawdown, recovery, exposure, long/short breakdown, session/regime breakdown and stability across date windows.
- Include a random-entry or shuffled-signal control and parameter-neighbourhood checks to detect overfit.
- Reject strategies that only work on one day or one narrow parameter setting. A one-day replay is a pipeline smoke test, not performance evidence.
- Final promotion requires native MT5 **Every Tick Based on Real Ticks** on broker-native PXBTTrading-1 history, cost/drawdown review, and demo forward evidence. Live execution remains blocked.
