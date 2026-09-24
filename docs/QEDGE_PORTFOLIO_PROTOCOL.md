# ASTRA QEDGE Portfolio Protocol

## Objective

Test several **independent XAUUSD strategy families** on the same reproducible
five-year bid/ask dataset and compare them on the same research standard.

This protocol deliberately separates:

1. signal discovery;
2. timeframe selection;
3. historical holdout;
4. rolling walk-forward;
5. execution stress;
6. native MT5 confirmation;
7. forward-demo evidence.

No stage authorizes live-money execution.

## Dataset

Pinned external XAUUSD M1 bid/ask OHLC:

- start: 2021-08-20
- end: 2026-08-20
- source transport: pinned GitHub mirror already used by AUREON research
- approximately 2.6 million M1 observations before active-market filtering

The Python research engine consumes the original independent bid/ask OHLC,
not the reduced MT5 custom-symbol representation.

## Independent strategies

### QEDGE-01 — Liquidity Sweep Reversal

Liquidity pool sweep → reclaim → execution-TF MSS → displacement → next-bar
entry. This is the closest Python research analogue to the current ASTRA EA.

### QEDGE-02 — Trend Pullback Continuation

Trend-TF EMA structure and slope → liquidity-TF pullback into the EMA 9/21
zone → execution-TF structural break → next-bar entry.

### QEDGE-03 — Expansion Breakout Retest

Liquidity-TF range breakout with displacement/body-efficiency requirements →
execution-TF retest and directional close → next-bar entry.

### QEDGE-04 — London Liquidity Raid

Completed 00:00–07:00 UTC Asian range → London-window raid beyond one side →
reclaim → next-bar entry.

### QEDGE-05 — New York Continuation / Reversal

Completed London range → New York continuation when trend-aligned, otherwise a
clear London-range raid/reclaim reversal.

## Timeframe cascades

Each strategy is evaluated independently on:

- M1 → M5 → M15 → H1
- M4 → M20 → H1 → H4
- M5 → M15 → H1 → H4
- M10 → M30 → H2 → H6
- M15 → H1 → H4 → H12

This is intentionally smaller than the earlier exhaustive timeframe DOE.
The exhaustive DOE already established which horizons generated useful sample
sizes. The portfolio protocol focuses compute on plausible cascades.

## Common execution model

To compare signal families fairly, initial discovery uses the same exit model:

- entry: next execution bar open after the signal closes;
- BUY entry at ask, SELL entry at bid;
- BUY exits use bid extremes, SELL exits use ask extremes;
- same-bar SL + TP ambiguity resolves to SL;
- initial target: 2R;
- standard maximum hold: 8 clock hours, converted to the relevant entry-TF bars;
- one open campaign per strategy/timeframe variant;
- outcome unit: R-multiple.

Partial exits, trailing, scale-ins and percentage risk are intentionally
excluded from the initial portfolio comparison. Those are execution/risk
overlays and must not manufacture signal alpha.

## Selection protocol

For each strategy, the cascade is selected **only** from the development
sample using:

- independent campaign count;
- expectancy in R;
- PF in R;
- R drawdown;
- sample-aware shrinkage.

Minimum preferred development evidence:

- 30 independent campaigns;
- positive expectancy;
- PF > 1.

The historical holdout is then examined only after selection.

The 2026-04-20 → 2026-08-20 historical holdout is useful validation evidence,
but it is not described as truly future-unseen because the wider project has
already inspected that market period in other studies.

## Rolling walk-forward

The companion `qedge_walkforward.py` uses:

- 18-month training window;
- 6-month frozen test window;
- 6-month roll.

At every step the cascade is selected from the training window only and then
frozen for the next test window.

## Portfolio analysis

Selected strategy variants are combined on an equal-risk basis.

The report includes:

- daily R correlation;
- portfolio net R;
- mean daily R;
- positive-day fraction;
- portfolio drawdown in R.

Diversification is not assumed. Highly correlated or individually negative
strategies are not retained merely to create a larger portfolio.

## Promotion rules

A strategy remains **RESEARCH** unless it later survives:

1. adequate independent sample size;
2. positive development evidence;
3. historical holdout support;
4. rolling walk-forward support;
5. parameter-neighborhood stability;
6. spread/slippage/delay/missed-fill stress;
7. bootstrap and block-bootstrap stress;
8. selection-bias controls;
9. native MT5 confirmation;
10. broker-native symbol/tick/execution validation;
11. forward-demo shadow evidence.

The final future-unseen gate is forward observation after the research rules
are frozen.
