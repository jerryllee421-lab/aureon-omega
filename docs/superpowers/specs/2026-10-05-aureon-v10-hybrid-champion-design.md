# AUREON Ω V10 — HYBRID CHAMPION Design

Date: 2026-10-05
Status: Design approved in chat; implementation not yet started
Target: XAUUSD / Gold, MetaTrader 5, research + DEMO validation before any LIVE consideration

## 1. Objective

Build a new AUREON Ω V10 Hybrid Champion EA that restores the high-frequency alpha characteristics of the proven FVG V2.17 line while preserving the newer execution-risk, telemetry, structural context, and profit-protection improvements developed through V9.7.

V10 is not a continuation of the increasingly restrictive V9.x control stack. The architecture intentionally separates the alpha engine from the intelligence/risk overlay so contextual features can rank and size opportunities without choking trade generation.

Primary success criteria for the first V10 candidate:

- Run on XAUUSD with M1 execution using 100% real ticks where available.
- Recover materially higher opportunity frequency than V9.7.
- Maintain positive expectancy and Profit Factor clearly above 1.0 before promotion.
- Keep drawdown governed by explicit risk controls rather than by suppressing all trade flow.
- Measure long and short performance independently.
- Measure first-entry and repeat-entry performance per FVG.
- Record enough telemetry to attribute performance to FVG, IFVG, liquidity, VWAP/value-area, EMA100/regime and exit-management features.
- Keep LIVE execution blocked until research and DEMO certification gates are met.

## 2. Baseline Evidence

### V2.17 lineage

Use `FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5` as the primary alpha-engine reference.

Important characteristics to preserve or port:

- M1 entry timeframe.
- FVG discovery and rejection/retest behavior.
- Long and short participation.
- Bias filter optional rather than mandatory.
- Midpoint requirement optional.
- Rejection confirmation enabled by default.
- Aggressive FVG persistence and replacement behavior.
- Repeated entries allowed on the same FVG (`InpOneTradePerFVG=false`).
- Zero-cooldown capability.
- Position and FVG attribution telemetry.
- Benchmark drift telemetry.
- Staged profit locking.
- ATR trailing, including the historically aggressive 0.10 ATR trail baseline.
- Spread/slippage monitoring.
- Execution retry and broker-stop validation hardening.

Historical benchmark reference only, not a guarantee:

- Win rate: 68.06%
- Profit Factor: 2.48

These values are used as comparison telemetry, not as implementation acceptance criteria.

### V9.7 lineage

Use `AUREON_OMEGA_V9_7_SUPER_SCALPER_EDGE_REPAIR.mq5` as the intelligence/risk-shell reference.

Preserve or adapt:

- Risk Governor with daily-loss and equity-drawdown controls.
- Tester applicability for the same governor.
- Evidence logging.
- VWAP / anchored VWAP / London VWAP context.
- POC / VAL / VAH / value-area context.
- Structural and liquidity-context features.
- MFE tracking.
- MFE giveback protection.
- Stagnation handling where evidence supports it.
- Setup/readiness telemetry.
- State persistence where required.

Do not preserve V9.7 behavior that caused excessive signal suppression or severe long-side under-participation.

## 3. Architectural Principle

V10 is split into four layers:

1. **Alpha Engine** — finds tradable FVG/IFVG opportunities and produces raw trade intents.
2. **Intelligence Scoring** — scores context and direction but does not impose broad all-or-nothing vetoes.
3. **Risk & Execution Governor** — validates account, symbol, spread, slippage, volume, stop geometry and risk limits.
4. **Position Manager** — captures profits using staged locks, ATR trailing and MFE-aware protection.

The key rule is:

> Intelligence should rank, size, and downgrade opportunities before it blocks them.

Only genuine safety, invalidation, or execution-integrity conditions may hard-block a trade.

## 4. Timeframe Model

### Execution

- Primary execution timeframe: M1.
- FVG formation, rejection/retest and repeated-entry handling occur on M1.

### Context

Context modules may consume M5/M15/H1 data where useful, but they must not create hidden look-ahead or stale-data dependencies.

Initial context set:

- M5 microstructure confirmation.
- M15 regime classification.
- H1 optional higher-timeframe trend context.

Each context module must expose a validity flag. Invalid or unavailable optional context must lower confidence rather than silently fabricate a value.

## 5. Alpha Engine

### 5.1 FVG discovery

Port V2.17 FVG discovery as the frozen starting point.

Required fields per FVG:

- unique FVG id
- bullish/bearish direction
- formation time
- low/high bounds
- midpoint
- width in ATR
- displacement/body metrics
- age in bars
- active/invalidated state
- entries already taken
- last entry/exit time
- last outcome in R

### 5.2 IFVG state

Add explicit IFVG lifecycle classification:

- FVG_FRESH
- FVG_PARTIALLY_MITIGATED
- FVG_FULLY_MITIGATED
- IFVG_BULLISH
- IFVG_BEARISH
- INVALID

IFVG is a distinct setup class and must be identifiable in telemetry.

### 5.3 Entry classes

Every candidate is assigned one of:

- **A+** — strongest confluence; standard/full research risk allocation.
- **A** — normal edge; standard or slightly reduced allocation.
- **B** — micro-scalp; reduced allocation and tighter management.
- **BLOCKED** — safety or hard invalidation only.

### 5.4 Re-entry

Repeated entries on the same FVG are allowed by design.

V10 must track:

- entry number on FVG
- previous entry outcome
- elapsed bars/time since prior exit
- FVG state at re-entry

Re-entry may be downgraded or blocked after repeated poor outcomes, but the default architecture must preserve the aggressive V2.17 capability.

## 6. Intelligence Scoring

Scoring is asymmetric by direction. Long and short models maintain separate thresholds and telemetry.

Initial score components:

### Core alpha score

- FVG width/quality
- displacement body ATR
- displacement body ratio
- rejection quality
- FVG age
- repeat-entry number

### Liquidity / structure

- liquidity sweep
- MSS/BOS confirmation
- local swing interaction
- previous-day high/low interaction
- Asia range interaction

### VWAP / profile

- daily VWAP position
- London VWAP position
- anchored VWAP position
- VWAP slope
- POC proximity
- VAL/VAH location
- value-area reclaim

### Regime

- EMA100 slope and price side
- M15 trend/range regime
- optional ADX/regime quality

### AMD

Classify the local state as:

- accumulation
- manipulation
- distribution
- unknown

AMD contributes to score only when classification confidence is sufficient.

### Direction-specific thresholds

Long and short trigger thresholds are independent.

Reason: V9.7 demonstrated large directional asymmetry. V10 must learn from that evidence rather than force symmetric gating.

## 7. Hard Blocks

The following may hard-block execution:

- non-XAU symbol when Gold enforcement is enabled
- invalid/stale tick
- invalid broker symbol specification
- invalid volume normalization
- invalid stop/freeze geometry
- spread above configured production limit
- slippage expectation above configured limit
- insufficient margin
- duplicate intent/ticket state
- unresolved position/state mismatch
- daily-loss limit reached
- drawdown limit reached
- LIVE account when running a DEMO-only build
- explicit FVG invalidation

RSI, ADX, EMA, VWAP and profile features are not hard blockers in the base V10 research configuration unless later evidence justifies a narrow rule.

## 8. Risk Model

Initial research defaults:

- risk percent remains configurable
- hard effective-risk cap must remain active
- daily-loss governor active
- equity-drawdown governor active
- governor applies in Strategy Tester
- one-account/symbol state consistency required

Risk allocation is modulated by setup grade:

- A+: 1.00 × configured research risk
- A: 0.75–1.00 ×
- B: 0.25–0.50 ×

Exact multipliers are parameters for research, not hard-coded profitability assumptions.

## 9. Position Management

V10 starts from the V2.17 profit-management model, then adds evidence-driven MFE protection.

### Stage 1 — early protection

- Lock1 around +0.50R → protect small positive R.
- Lock2 around +1.00R → protect larger positive R.

### Stage 2 — ATR trail

- ATR trail activates around the V2.17 baseline trigger.
- Initial benchmark trail distance: 0.10 ATR.
- Tightening may be conditional on setup class and realized MFE.

### Stage 3 — MFE giveback

MFE protection may close or tighten a trade only after minimum favorable excursion is reached.

The mechanism must be subordinate to the primary trail so it does not reproduce V9.7's tendency to over-cut runners.

### Stagnation

Stagnation exit is disabled or lenient in the first V10 benchmark unless evidence proves it improves expectancy. V9.7 reduced average hold but also reduced trade count and payoff quality.

## 10. Telemetry

Every entry and exit must be attributable.

Required fields include:

- timestamp
- symbol
- direction
- FVG id
- FVG state
- entry number on FVG
- setup grade
- raw alpha score
- intelligence score
- long/short threshold
- FVG geometry
- displacement metrics
- sweep/MSS/BOS state
- IFVG state
- VWAP values/distances
- POC/VAL/VAH values/distances
- EMA100/regime state
- AMD state/confidence
- spread
- requested vs actual entry
- slippage
- volume
- SL/TP
- MFE/MAE in R
- realized R
- exit reason
- cumulative win rate
- cumulative PF
- account drawdown

Telemetry must distinguish first entries from repeated entries on the same FVG.

## 11. Execution Safety

Preserve V2.17 execution hardening:

- broker stop/freeze validation
- transient error retry only
- requested vs actual entry tracking
- position verification after fill

Preserve AUREON safety posture:

- DEMO-only when execution is armed for forward validation
- LIVE fail-closed
- XAU enforcement
- stale-data rejection
- risk-governor fail-closed

## 12. Testing Strategy

### Phase A — compile gate

- MetaEditor compile
- 0 errors
- warnings reviewed and resolved where practical

### Phase B — deterministic regression

Verify:

- FVG discovery
- IFVG transition
- repeated FVG entries
- grade calculation
- direction-specific scoring
- lot normalization
- stop validation
- risk-governor behavior
- MFE/MAE tracking
- exit reason attribution

### Phase C — primary benchmark

Run XAUUSD M1 using Every tick based on real ticks.

First benchmark should cover the same broker/data environment used for previous V2.17/V9.x work where possible.

Primary comparisons:

- trade count
- PF
- WR
- expectancy
- Sharpe
- max relative equity DD
- average hold time
- long PF/WR
- short PF/WR
- first-entry PF
- repeat-entry PF by entry number

### Phase D — ablation

At minimum:

1. pure V2.17-style core
2. + VWAP/profile score
3. + liquidity/structure score
4. + EMA100/regime score
5. + AMD score
6. + IFVG scoring
7. + MFE overlay

Promote only features that improve robustness, not merely in-sample net profit.

### Phase E — out-of-sample / forward

- unseen historical segment
- walk-forward where practical
- DEMO forward execution
- spread/slippage drift monitoring

## 13. Promotion Criteria

The first V10 candidate is a research challenger, not an automatic replacement for V2.17.

Promotion requires:

- materially higher sample count than V9.7
- PF > 1.0 with positive expectancy in the primary run
- acceptable drawdown under active governor
- no catastrophic directional asymmetry
- repeat-entry behavior supported by telemetry
- no unresolved state or execution-integrity errors
- no degradation severe enough to fail unseen-period validation

A later production candidate should target PF >= 1.5 and stable out-of-sample behavior, but these are aspirational research thresholds rather than guaranteed outcomes.

## 14. File and Versioning Plan

Primary source:

`AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`

Preserve as frozen references:

- `FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5`
- `AUREON_OMEGA_V9_7_SUPER_SCALPER_EDGE_REPAIR.mq5`

Do not overwrite either baseline.

## 15. Non-Goals for V10 Candidate 1

- no broker-independent HFT claims
- no AI/API dependency for trade permission
- no LIVE enablement
- no martingale
- no grid recovery
- no opaque self-modifying parameters
- no profit guarantees
- no attempt to maximize trade count at the expense of expectancy

## 16. Implementation Order

1. Establish V2.17-derived M1 FVG core in V10 namespace.
2. Add explicit FVG/IFVG lifecycle and repeated-entry attribution.
3. Port V9.7 risk governor and DEMO/LIVE guards.
4. Port VWAP/profile context as scoring only.
5. Add liquidity/structure scoring.
6. Add EMA100/regime scoring.
7. Add AMD classifier/scoring.
8. Add asymmetric long/short thresholds and setup grades.
9. Merge V2.17 staged locks + ATR trail with restrained MFE giveback.
10. Add complete telemetry and dashboard.
11. Run compile/static verification.
12. Produce the first downloadable V10 `.mq5` candidate for Strategy Tester.

## 17. Decision

Recommended architecture: **V2.17 alpha engine + V9.7 intelligence/risk shell**.

This design intentionally restores aggressive M1 opportunity capture while keeping newer controls focused on risk, attribution, and ranking rather than broad signal suppression.
