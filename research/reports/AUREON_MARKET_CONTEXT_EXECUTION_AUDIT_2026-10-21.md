# AUREON Ω — Market-Context and Execution Audit
Date: 2026-10-21

## Executive finding

The current strategy suite is not yet testing a clean enough execution model to determine which market context creates edge. This audit found a concrete cost-timing defect in the offline replay: entry spread cost was based on the *average spread across the entire entry M5 bar*, even though the entry is modeled at that bar's open. That average contains quotes observed after the entry time. This is not a direct signal-price lookahead, but it is a point-in-time accounting defect and makes cost attribution inconsistent.

## Fix applied in research branch

- Preserve mean spread for descriptive diagnostics and the signal-bar spread filter.
- Add `spread_open` from the first quote in each M5 bar and use it for entry cost.
- Add `spread_max` and use the maximum spread in the exit M5 bar as a conservative cost bound. This intentionally errs against the strategy, but it is not an exact fill model; exact exit-time spread requires quote-level execution replay.
- Reject entry if the first-quote spread of the next bar exceeds 0.80 price units, even if the signal bar itself passed the spread filter.
- Add a regression test proving open, mean, and maximum spread are distinct and computed as expected.

## Market-context diagnosis from the existing short sample

The existing 20-day third-party Dukascopy archive is insufficient to infer stable regime-conditioned expectancy. What it does show:

- Daily CRT: full-sample PF 1.28, but 13 OOS trades net -10.13 price units and PF 0.82; its third chronological fold is negative. Treat as a hypothesis, not an edge.
- AMD session: overall net -36.49; 12 OOS trades net -2.93 and PF 0.95. UTC session definitions are not verified against PXBT server time.
- FVG scalper: 77 trades, net -16.68, PF 0.94; fold net degrades from +33.13 to -10.66 to -39.15. Strong instability signal.
- Gold trap: 123 trades, net -168.81, PF 0.69; negative across all three folds.
- H1 breakout, session breakout, and session VWAP+EMA are negative on the available sample.
- Daily swing has zero trades because the sample is shorter than its 50-completed-daily-bar requirement; it is untested, not disproven.
- M5 mean reversion has only one trade; no inference is justified.

## Further execution defects / limitations still open

1. **M5 OHLC exit ordering:** when both stop and target are touched in one M5 candle, stop-first is a conservative rule but does not reconstruct the actual quote sequence. A tick-level exit simulator is required for reliable ranking.
2. **Fill price abstraction:** entries and exits are represented by midpoint OHLC plus spread/slippage deductions. This is not the same as buying at ask and selling at bid on each actual quote.
3. **Session labels:** UTC is a proxy. PXBT server time, session boundaries and DST need verification.
4. **Market-regime attribution:** existing reports do not yet provide a robust regime × session × setup × direction breakdown with sufficient independent trades per cell. Do not infer a best regime from tiny bins.
5. **Sample/provenance:** archive is third-party Dukascopy, only about 20 days, and not verified PXBTTrading-1 native ticks.
6. **Broker economics:** commission, swap, contract size, tick value and ZAR conversion remain unverified.

## Next investigation sequence

1. Run CI regression tests for this cost-timing correction.
2. Implement quote-level execution: enter on first eligible tick after the completed M5 signal, buy at ask/sell at bid, and evaluate stop/target against executable quotes in chronological order.
3. Add causal regime labels computed only from completed bars: volatility percentile, trend strength/slope, range-vs-expansion, and session. Freeze the definitions before evaluating.
4. Report per-strategy and pooled trade expectancy by regime/session/direction, with sample counts and uncertainty; mark thin cells inconclusive.
5. Evaluate on longer data using anchored walk-forward splits and a locked final holdout. Do not optimize the holdout.
6. Reproduce finalists in MT5 Strategy Tester using broker-native “Every Tick Based on Real Ticks” and verified PXBT costs.

## Release status

**NO STRATEGY APPROVED. DEMO ONLY. LIVE BLOCKED. Frozen V2.12 remains unchanged.**

This audit is a research engineering update, not a profitability claim.
