# AUREON Ω V10.5 — Market Intelligence / Pre-Live EA Design

Date: 2026-10-04
Status: Design freeze for review; implementation must not begin until this written spec is approved.
Target: XAUUSD / Gold, MT5, mobile-friendly deployment workflow, native Strategy Tester + DEMO forward validation.
Live trading: HARD BLOCKED throughout V10.5 development and certification.

## 1. Objective

Build the next AUREON Ω challenger by combining the strongest proven parts of the existing EA lineage with a correctly engineered market-intelligence stack:

- liquidity sweeps and reclaim
- AMD / Accumulation-Manipulation-Distribution context
- MSS / structure shift and displacement
- FVG and IFVG
- VWAP / anchored VWAP / value-area context
- volume-at-price
- broker-aware tick/order-flow intelligence
- 5s/15s/30s microstructure timing
- execution-cost and broker-spec realism
- restart-safe risk and reconciliation

The goal is not to maximize backtest balance or trade count. The goal is to improve repeatability, execution integrity, and risk-adjusted performance while preserving the edge found in prior AUREON/FVG controls.

No module is promoted because it sounds sophisticated. Every new module starts as measurable telemetry/shadow logic and must survive controlled ablation, out-of-sample testing, stress testing, and DEMO forward validation.

## 2. Existing control that must be preserved

V10.4 remains the immediate control for this development lane. The repository also retains the frozen V2.12 high-growth benchmark and later V2.17 evidence as historical controls.

V10.4 functionality that must not regress:

- completed-bar/no-lookahead research logic
- previous-day and Asia/session structure
- M1 ordered sequence: raid -> reclaim -> MSS -> displacement -> FVG -> retrace
- EMA100 H1/M5 context and M1 EMA21 timing
- daily/London/anchored VWAP
- POC/VAH/VAL bar-derived profile
- 5s/15s/30s tick-aggregated price microstructure
- spread/slippage/net-edge checks
- one-position policy
- 6-second anti-churn floor
- 200-trades/day failsafe ceiling
- direction-specific loss-streak quarantine
- daily-loss and equity-drawdown governors
- exact position reconciliation and duplicate-close protection
- persistent telemetry and forward-drift monitoring
- TESTER/DEMO execution only; LIVE hard blocked

V10.5 must be a challenger. It does not replace a control until evidence justifies promotion.

## 3. Non-negotiable engineering rules

### 3.1 No fabricated market data

If PXBT does not expose a data field, V10.5 must not invent it or label a proxy as the real quantity.

### 3.2 Explicit data-quality tiers

All volume and order-flow decisions carry a source-quality grade:

- `FLOW_NONE`: no usable flow data
- `FLOW_QUOTE_INFERRED`: direction inferred from quote/tick movement
- `FLOW_TRADE_INFERRED`: trade ticks exist but aggressor side is inferred
- `FLOW_TRADE_NATIVE`: broker provides usable trade price/volume and side information
- `FLOW_DOM`: current Depth-of-Market information is available

A decision may use a lower-quality source, but telemetry must record that fact and thresholds must be calibrated separately.

### 3.3 No backtest/forward mismatch hidden by design

DOM is not assumed to exist historically in MT5 Strategy Tester. DOM may enhance DEMO forward decisions, but no strategy is declared historically validated if the decisive gate only existed in forward testing.

Backtestable and forward-only features must be reported separately.

### 3.4 Closed data for structural signals

M1/M5/H1 structural features use completed bars unless the feature is explicitly part of the real-time microstructure/order-flow layer.

### 3.5 No live-risk promotion from AI or score alone

Readiness scores are evidence summaries, not probabilities of winning and not permission to increase risk.

## 4. Proposed architecture

The V10.5 decision pipeline is:

`Market Truth -> Regime -> Liquidity Map -> AMD State -> Structure/MSS -> Displacement -> FVG/IFVG -> VWAP/Profile -> Order Flow -> Micro Trigger -> Execution Gate -> Risk Governor -> TradeIntent -> Broker -> Reconciliation -> Evidence`

Each stage emits an inspectable state object. Failure of an essential stage fails closed; optional context stages reduce confidence/readiness rather than inventing confirmation.

## 5. Market Truth layer

The Market Truth layer owns raw broker observations and data quality.

Inputs:

- closed M1/M5/M15/H1/H4 bars
- current `MqlTick`
- historical ticks through `CopyTicks` / `CopyTicksRange` where available
- broker symbol specification
- current spread
- trade-mode/filling-mode/stops/freeze/volume specifications
- current DOM through `MarketBookAdd` / `MarketBookGet` only when broker-supported

Outputs include freshness timestamps and source-quality flags.

No strategy module reads undocumented or stale values directly from the terminal.

## 6. Liquidity Map engine

The existing prior-20-bar sweep remains available as a control but is no longer the only liquidity reference.

The map contains separately typed levels:

1. Previous trading day high / low
2. Asia-session high / low
3. London-session developing high / low
4. New York-session developing high / low
5. confirmed swing/pivot highs and lows
6. equal-high / equal-low clusters
7. recent local liquidity pools
8. FVG / IFVG boundaries
9. VAH / VAL / POC and VWAP deviation levels as location references

Important distinction: VWAP/profile levels are not automatically labelled stop-liquidity. They are location/acceptance references unless price action demonstrates sweep/rejection behavior.

### 6.1 Sweep classification

Every candidate sweep records:

- level type
- level price
- direction
- penetration in points and ATR
- wick/body relationship
- close/reclaim distance
- sweep age
- subsequent MSS/displacement status

Classes:

- `TOUCH`
- `SHALLOW_SWEEP`
- `VALID_SWEEP`
- `DEEP_SWEEP`
- `FAILURE/BREAK_ACCEPTANCE`

A valid reversal sweep requires penetration plus reclaim, not merely a touch.

## 7. AMD / Power-of-Three engine

AMD is implemented as a state machine, not a visual label.

### 7.1 ACCUMULATION

Candidate range must show:

- bounded high/low for a minimum age
- compressed range relative to ATR
- repeated containment/acceptance
- no confirmed distribution break yet

Optional supporting evidence:

- declining directional efficiency
- contracting realized range
- balanced inferred delta
- POC/value stability

### 7.2 MANIPULATION

Manipulation requires an external-liquidity event outside the accumulation range:

- sweep beyond range high for bearish setup, or
- sweep below range low for bullish setup

The sweep must then reclaim the range or demonstrate rejection. A clean breakout with sustained acceptance is classified as breakout/distribution, not manipulation.

### 7.3 DISTRIBUTION

Distribution requires directional confirmation after manipulation:

- MSS / structure shift
- displacement
- directional imbalance/FVG or IFVG
- continuation away from the manipulation extreme

AMD state is timestamped and expires. It cannot remain valid indefinitely.

## 8. FVG engine

Existing FVG logic is preserved as the control definition:

- 3-candle directional imbalance
- middle candle must meet displacement requirements
- minimum gap normalized by ATR
- formation after required MSS/displacement ordering
- freshness requirement
- retracement depth measured explicitly

V10.5 extends the zone metadata:

- origin time
- direction
- low/high
- size in points/ATR
- age
- fill percentage
- first-touch time
- attempt count
- whether created during AMD distribution
- whether associated with a liquidity sweep
- whether aligned with VWAP/value context
- lifecycle state: `FRESH`, `PARTIAL`, `MITIGATED`, `INVALIDATED`, `INVERTED`, `EXPIRED`

No same-zone unlimited rapid-fire re-entry is permitted.

## 9. IFVG engine

An IFVG is not just an opposite FVG. It is an existing FVG that fails and becomes a candidate inversion zone.

Proposed lifecycle:

1. valid FVG exists
2. price decisively closes through the invalidation side
3. original FVG becomes `INVERTED`
4. price retests the inverted zone from the opposite side
5. rejection/acceptance behavior is measured
6. MSS/displacement/order-flow confirmation determines whether it is actionable

Required fields:

- original FVG identifier
- inversion timestamp
- close-through distance in ATR
- retest timestamp
- retest depth
- rejection quality
- direction after inversion
- zone age / expiry

One original FVG may create at most one active inversion state unless research proves a different lifecycle is superior.

## 10. VWAP engine

V10.5 maintains three distinct concepts and labels them correctly.

### 10.1 Trade VWAP

Use only when the broker supplies usable trade price and volume. Formula uses actual observed trade price * trade volume.

### 10.2 Quote/tick VWAP proxy

When trade volume is unavailable, use quote/midpoint observations weighted by tick frequency. This is explicitly labelled a quote/tick proxy, not true exchange-volume VWAP.

### 10.3 Bar-derived VWAP fallback

Retain closed-M1 HLC3 weighted by real volume when available, otherwise tick volume. This remains the robust historical fallback.

Contexts:

- daily
- London
- New York
- anchored to liquidity manipulation/sweep
- optional anchored to major displacement origin

Outputs:

- VWAP
- slope
- distance in ATR
- sigma bands
- reclaim/rejection state
- source quality

## 11. Volume-at-price / Profile engine

The current equal-distribution-across-candle-range profile is retained only as the bar-profile control.

V10.5 preferred hierarchy:

1. trade-volume-at-price when broker trade ticks contain usable volume
2. tick-frequency-at-price profile when only quote ticks exist
3. M1 bar-derived profile fallback

Outputs:

- POC
- VAH / VAL
- HVN
- LVN
- developing POC
- POC migration direction/rate
- value-area width and expansion/contraction
- acceptance/rejection outside value
- profile source-quality label

The engine must not claim centralized Gold futures volume when running on a CFD feed.

## 12. Order-flow engine

Order flow is source-aware.

### 12.1 Native trade delta

When broker ticks contain sufficient trade-side information:

- aggressive buy volume
- aggressive sell volume
- delta
- cumulative delta (CVD)

### 12.2 Inferred tick delta

When aggressor side is not supplied, infer direction using a deterministic hierarchy such as:

1. trade/last price versus bid/ask where available
2. uptick/downtick rule
3. midpoint movement
4. unchanged-tick carry rule with capped persistence

Telemetry identifies all inferred observations.

### 12.3 Flow windows

Maintain rolling metrics for at least:

- 5 seconds
- 15 seconds
- 30 seconds
- 60 seconds
- session-to-date CVD where meaningful

Metrics:

- signed delta
- normalized delta
- buy/sell imbalance
- tick velocity
- velocity acceleration
- spread expansion/contraction
- directional efficiency
- delta/price divergence

## 13. DOM engine

DOM is an optional real-time confirmer.

If available:

- top-N bid quantity
- top-N ask quantity
- distance-weighted imbalance
- microprice
- best-level replenishment
- stacking/pulling proxies
- bid/ask liquidity persistence

If unavailable, set `DOM_UNAVAILABLE` and continue with the appropriate lower-quality path. Never synthesize DOM.

DOM-dependent performance is evaluated in DEMO forward testing separately from historical Strategy Tester performance.

## 14. Absorption, exhaustion and divergence

### Absorption

Candidate absorption requires aggressive/inferred flow pressure with unusually limited price progress and evidence of opposing-side persistence/rejection.

### Exhaustion

Candidate exhaustion requires new price extension while flow/velocity fails to confirm or collapses.

### Delta divergence

Examples:

- higher price high with weaker positive delta/CVD
- lower price low with weaker negative delta/CVD

These are supporting evidence, not automatic reversal entries.

## 15. Regime-aware setup families

V10.5 must not apply one universal confirmation rule to every setup.

### 15.1 Liquidity reversal

Preferred sequence:

`external liquidity sweep -> reclaim -> MSS -> displacement -> FVG/IFVG -> VWAP/value location -> flow reversal/absorption -> micro trigger`

### 15.2 Trend continuation

Preferred sequence:

`HTF trend/regime -> pullback into VWAP/FVG/value location -> same-direction structure -> displacement -> same-direction flow -> micro trigger`

### 15.3 Breakout / expansion

Preferred sequence:

`compression/accumulation -> valid range acceptance break -> volume/tick-velocity expansion -> directional flow -> retest/continuation`

A breakout that is accepted outside the range must not be misclassified as AMD manipulation.

## 16. Decision fusion

V10.5 uses evidence categories rather than a monolithic arbitrary score.

Categories:

- context/regime
- liquidity
- AMD state
- structure
- imbalance/FVG/IFVG
- VWAP/profile location
- flow quality
- micro timing
- execution quality
- risk state

Each category returns:

- state (`PASS`, `NEUTRAL`, `FAIL`, `UNAVAILABLE`)
- numeric evidence score for telemetry
- source quality
- contradictions

Hard gates are limited to conditions that truly invalidate execution, such as stale data, invalid symbol specification, unresolved reconciliation, unacceptable spread/slippage, missing protective stop, or explicit strategy invalidation.

Optional data such as DOM may improve a decision but cannot silently make historical and forward logic incomparable.

## 17. Entry state machine

Canonical reversal candidate lifecycle:

`SCANNING`
-> `LIQUIDITY_IDENTIFIED`
-> `SWEPT`
-> `RECLAIMED`
-> `MSS_CONFIRMED`
-> `DISPLACED`
-> `FVG_OR_IFVG_READY`
-> `RETESTING`
-> `FLOW_CONFIRMED`
-> `MICRO_ARMED`
-> `TRIGGERED`

Terminal states:

- `INVALIDATED`
- `EXPIRED`
- `BLOCKED_EXECUTION`
- `BLOCKED_RISK`
- `DEGRADED_DATA`

Every transition is timestamped and logged.

## 18. Stops and targets

### Stops

SL candidates are structural and broker-valid:

- beyond manipulation/sweep extreme
- beyond FVG/IFVG invalidation
- beyond confirmed swing structure
- ATR safety buffer

The selected stop must respect broker minimum stop/freeze constraints and maximum risk-distance rules.

### Targets

Candidate target map:

- nearby liquidity pool
- opposing session high/low
- POC
- VAH/VAL
- VWAP/anchored VWAP
- HVN/LVN transition
- fixed-R fallback

TP1/TP2/TP3 remain ordered and must satisfy minimum R constraints after costs.

## 19. Risk and execution controls

Retain V10.4 safety as the starting point:

- default DEMO risk 0.05%
- absolute configured cap 0.10% during initial certification
- one managed position
- 3% daily loss halt
- 6% equity drawdown halt
- anti-churn minimum spacing
- direction-specific loss-streak quarantine
- 200-trades/day runaway ceiling
- no martingale
- no grid
- no loss-recovery lot multiplier

Directional risk multipliers remain a research hypothesis and must be ablated; they are not treated as permanent truth.

Before each order:

- DEMO/tester authority check
- LIVE hard block
- symbol/trade-mode validation
- tick freshness
- spread limit
- slippage expectation
- stop/freeze levels
- volume min/max/step
- margin calculation
- filling mode
- one-position/reconciliation check
- daily/DD governor
- duplicate TradeIntent prevention

## 20. Restart/reconciliation requirements

V10.4 reliability behavior is mandatory:

- exact 64-bit position identifiers
- durable state snapshot
- idempotent close accounting
- broker-position reconciliation after restart
- fail-closed unresolved state
- zero orphan positions/orders
- no new entry while broker/local state is inconsistent

Order-flow/DOM state may be rebuilt after restart and must be marked warm-up/degraded until sufficient observations exist.

## 21. Telemetry

Every candidate and every actual trade writes inspectable evidence.

Minimum telemetry groups:

- signal ID / TradeIntent ID
- timestamps
- regime
- liquidity level type/price
- sweep depth/reclaim quality
- AMD phase
- MSS/displacement
- FVG/IFVG metadata
- VWAP/profile values and source quality
- flow source quality
- delta/CVD windows
- velocity/acceleration
- absorption/exhaustion/divergence states
- DOM metrics when available
- readiness/evidence categories
- contradictions
- spread/slippage/cost-R
- entry/SL/TP1/TP2/TP3
- volume/risk
- broker ACK/deal/position identifiers
- MAE/MFE
- realized R
- exit reason
- reconciliation result

No telemetry field may imply real volume/order flow if the underlying source is inferred.

## 22. Development structure and single-file release

For reliability and testability, implementation should be modular during development:

- `MarketTruth`
- `LiquidityMap`
- `AMD`
- `FVG_IFVG`
- `VWAP_Profile`
- `OrderFlow`
- `DecisionEngine`
- `RiskExecution`
- `Telemetry`

The user-facing release remains a single MQ5 EA. A deterministic build step may inline/assemble the reviewed modules into one release file so there are no manual runtime dependencies.

No external AI/API call is required for the deterministic execution loop.

## 23. Test-first development requirements

Each new deterministic behavior receives a failing test before implementation.

Required test groups:

### Liquidity
- valid sweep/reclaim
- touch is not sweep
- deep break is not reversal sweep
- equal-high/low clustering tolerance

### AMD
- accumulation detection
- manipulation sweep + reclaim
- accepted breakout does not become manipulation
- distribution confirmation
- expiry/reset

### FVG/IFVG
- bullish/bearish FVG
- displacement requirement
- freshness/partial mitigation
- invalidation
- inversion lifecycle
- retest/rejection

### VWAP/profile
- native trade VWAP math
- quote/tick proxy labelling
- bar fallback
- POC/VAH/VAL and HVN/LVN calculations
- source-quality fallback

### Order flow
- native side classification when flags exist
- deterministic inferred-side fallback
- CVD accumulation
- rolling-window eviction
- absorption/exhaustion/divergence behavior
- no fabricated flow on missing input

### DOM
- imbalance/microprice calculation
- unavailable DOM fallback
- warm-up behavior

### Execution
- hard LIVE block
- stale tick block
- spread/slippage block
- invalid stop/volume block
- duplicate intent block
- reconciliation block
- daily/DD governor

Native MetaEditor must finish with 0 errors and 0 warnings for the release candidate.

## 24. Backtest and ablation matrix

All performance claims require same-period controlled comparisons.

Minimum variants:

A. V10.4 control
B. + enhanced Liquidity Map only
C. + AMD only
D. + IFVG only
E. + tick/profile upgrade only
F. + backtestable inferred order flow only
G. full backtestable V10.5 stack
H. full stack minus each major module, one at a time

DOM is not folded into historical claims unless historical depth evidence exists. DOM gets a separate DEMO-forward comparison.

Required evaluation:

- native MT5 Every Tick Based on Real Ticks
- same-period parity
- untouched OOS periods
- chronological walk-forward
- spread/slippage/commission stress
- +50% execution-cost stress
- long/short split
- session split
- regime split
- month/quarter stability
- parameter-neighbour stability
- Monte Carlo realized-R paths
- trade-frequency and clustering analysis
- compounding versus fixed-risk decomposition

## 25. Promotion criteria

No single headline balance is sufficient.

A V10.5 candidate should not advance unless evidence supports all of the following:

- native compile: 0 errors / 0 warnings
- trustworthy real-tick history coverage
- positive OOS expectancy after costs
- OOS PF target >= 1.50; >= 2.00 preferred
- drawdown materially controlled; target <= 15%, reject/reevaluate near or above 20%
- remains positive under materially worse execution costs
- no single month/session/direction explains most of the edge
- no pathological same-zone rapid-fire loop
- no material lookahead or bar-order ambiguity
- state/reconciliation tests pass
- DEMO forward sample progresses through 20, 50, then 100 genuine trades
- zero unresolved broker/local mismatches
- zero orphan positions
- forward slippage/spread drift remains acceptable

Only after this stage should a separate LIVE-candidate design be discussed.

## 26. Explicit exclusions from V10.5

- no forced 1,000-trades/day quota
- no martingale/grid
- no self-modifying live parameters
- no unverified AI trade authority
- no fabricated centralized order book
- no assumption that CFD tick volume equals exchange Gold futures volume
- no automatic LIVE enablement
- no risk increase because historical compounding looks spectacular

## 27. Final definition of “ultimate” for this project

“Ultimate” means the most thoroughly validated, broker-aware and fail-closed AUREON candidate we can support with evidence. It does not mean guaranteed profitability, maximum trade count, or maximum backtest balance.

V10.5 is successful if it improves robustness and decision quality without destroying the proven edge, and if every claimed improvement can be traced to reproducible native MT5 and DEMO evidence.
