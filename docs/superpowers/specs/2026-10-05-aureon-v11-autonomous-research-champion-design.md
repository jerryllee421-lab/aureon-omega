# AUREON Ω V11 — AUTONOMOUS RESEARCH CHAMPION Design

Date: 2026-10-05
Status: Architecture approved in chat; implementation not yet started
Target: XAUUSD / Gold, MetaTrader 5 Strategy Tester, zero-manual-input research workflow

## 1. Objective

Build one self-contained MQL5 EA that replaces the slow candidate-by-candidate workflow with an autonomous multi-lane research engine. The user should only select the EA, XAUUSD, M1, real ticks, a date range, and press Start. All strategy parameters, research presets, scoring thresholds, risk settings, session definitions, and telemetry configuration are embedded in the file.

The system must first recover and verify a reproducible trading edge before any attempt to scale compounding. Million/billion backtest outcomes are not acceptance criteria by themselves; they are only meaningful after the underlying lane demonstrates positive expectancy, robust Profit Factor, acceptable drawdown, and out-of-sample stability.

## 2. Evidence Driving V11

Recent V10 experiments established four facts:

1. Candidate-2 generated thousands of trades but had a persistent losing edge (PF below 1 and near-total drawdown).
2. Blanket polarity reversal performed worse, proving that simple direction inversion is not the missing logic.
3. Candidate-4's FVG/IFVG lifecycle approach improved quality but over-filtered to only a handful of trades across the benchmark period.
4. Repeated one-file manual patching is too slow and obscures which feature actually adds or removes edge.

Therefore V11 must evaluate multiple research hypotheses concurrently on the exact same historical price stream.

## 3. Core Principle

One backtest run must evaluate many strategy lanes internally.

Only one lane may optionally place real Strategy Tester orders for sanity checks. All other lanes run as deterministic shadow trades using the same tick/bar stream. This avoids strategy interference and allows direct lane-to-lane comparison under identical market data.

## 4. Zero-Configuration Requirement

The EA must contain all defaults internally.

The user must not be required to change:

- risk
- FVG thresholds
- IFVG thresholds
- session windows
- VWAP settings
- EMA periods
- AMD settings
- liquidity settings
- re-entry controls
- SL/TP
- trailing
- MFE logic
- score thresholds
- spread/slippage assumptions
- lane selection
- telemetry filenames

The first V11 benchmark should run correctly with default inputs untouched.

## 5. Embedded Research Lanes

Candidate 1 must include these lanes:

### Lane A — Frozen V2.17 Control

Purpose: reproduce the original aggressive FVG behavior as faithfully as possible.

Characteristics:
- M1 FVG discovery
- original bullish/bearish continuation direction
- repeated FVG participation
- permissive filtering
- staged locks
- aggressive ATR trailing baseline

This lane is the control against which all newer intelligence is measured.

### Lane B — Controlled FVG Continuation

- original FVG direction
- max controlled re-entries per zone
- cooldown between re-entries
- same-zone loss quarantine

### Lane C — IFVG Reversal

- no reversal while original FVG still holds
- requires decisive invalidation
- requires opposite-side retest
- requires rejection confirmation

### Lane D — FVG + VWAP/Profile

Continuation/IFVG base logic plus:
- daily/session VWAP position
- VWAP slope
- POC/VAH/VAL proximity where data is available

These features score rather than broadly hard-block.

### Lane E — FVG + EMA100 Regime

- EMA100 price side
- EMA100 slope
- optional M15 regime context

### Lane F — FVG + Liquidity/Structure

- liquidity sweep
- local swing interaction
- MSS/BOS confirmation
- prior high/low interaction

### Lane G — FVG + AMD

- accumulation
- manipulation
- distribution
- unknown

AMD only contributes when classification confidence is sufficient.

### Lane H — Full Hybrid

Combines FVG/IFVG + VWAP/profile + EMA100 + liquidity/structure + AMD using weighted scoring.

### Lane I — London Session Focus

Same core alpha with London-focused session logic.

### Lane J — New York Session Focus

Same core alpha with New York-focused session logic.

## 6. Shadow Trade Engine

Each lane must maintain its own virtual account state.

Per lane track:
- virtual balance/equity
- open shadow position
- direction
- entry price/time
- volume or normalized risk units
- SL/TP
- initial risk in price and R
- MFE/MAE
- exit reason
- realized profit/loss
- realized R
- peak equity
- drawdown

Shadow execution must be deterministic and consume the same price stream as the tester.

## 7. Independent Lane Statistics

For every lane calculate:

- total trades
- wins
- losses
- win rate
- gross profit
- gross loss
- Profit Factor
- expected payoff
- expectancy in R
- max drawdown proxy
- average MFE
- average MAE
- average hold time
- long trades / WR / PF
- short trades / WR / PF
- first-entry performance
- repeat-entry performance by entry number
- session performance

## 8. Automatic Leaderboard

At OnTester/OnDeinit, print and export a ranked leaderboard.

Default ranking priority:

1. positive expectancy
2. PF
3. drawdown penalty
4. minimum sample-size gate
5. stability across directions/sessions

A lane with very high PF but too few trades must not automatically rank first.

The report must explicitly mark insufficient-sample lanes.

## 9. Minimum Sample Gates

Initial gates:

- < 30 trades: insufficient sample
- 30–99 trades: exploratory only
- 100–499 trades: usable research sample
- >= 500 trades: strong research sample

These labels are research guidance, not statistical guarantees.

## 10. Risk Normalization

To compare lanes fairly, all shadow lanes should default to normalized fixed fractional research risk.

Recommended first-pass normalization:
- 0.25% virtual risk per shadow trade
- no martingale
- no grid
- no lane-specific hidden compounding advantage

Optional compounding may be measured separately after edge validation.

## 11. Costs and Execution Assumptions

Every lane must include the same baseline friction model:

- spread from tester symbol/tick where possible
- configurable embedded slippage assumption
- broker stop/freeze constraints for any real tester execution lane
- no zero-cost fantasy fills

Cost assumptions must be written to telemetry.

## 12. FVG / IFVG State Model

Each tracked FVG must expose:

- id
- direction
- formed time
- low/high/midpoint
- width in ATR
- displacement metrics
- age
- entries taken
- last outcome
- state

States:
- FVG_FRESH
- FVG_PARTIALLY_MITIGATED
- FVG_HELD
- FVG_INVALIDATED
- IFVG_BULLISH
- IFVG_BEARISH
- EXPIRED

## 13. Re-entry Research

The engine must compare re-entry behavior rather than hard-code one answer.

At minimum record:
- first entry
- second entry
- third+ entry bucket
- prior outcome
- bars since prior exit

The leaderboard/report should reveal whether repeated entries actually add or destroy edge.

## 14. Session Research

Internally classify every trade by session bucket:

- Asia
- London
- London/NY overlap
- New York
- rollover/other

The initial EA may allow all shadow lanes to observe all periods while dedicated London and NY lanes enforce their own windows.

## 15. Exit Families

V11 must support internal comparison of at least:

- V2.17 staged lock + 0.10 ATR trail
- fixed-R exit baseline
- MFE-aware giveback protection

Candidate 1 does not need a combinatorial explosion. Each lane receives one predefined exit family so the first run remains interpretable.

## 16. Telemetry

Export one CSV with lane-qualified records.

Required fields:
- timestamp
- lane id/name
- symbol
- direction
- setup type
- FVG id/state
- entry number
- session
- score components
- entry
- SL/TP
- spread
- assumed slippage
- MFE/MAE
- realized R
- realized P/L
- exit reason
- lane balance/equity/DD

Also export the final leaderboard CSV.

## 17. Strategy Tester Integration

The EA must:

- run on XAUUSD M1
- use Strategy Tester real ticks when selected
- remain deterministic
- return a meaningful OnTester score for the currently designated champion lane or composite ranking
- print the leaderboard in the Journal at test end

## 18. Champion Selection

Candidate 1 must not automatically rewrite its own parameters.

It may identify the best lane, but promotion into a new champion configuration happens only after reviewing:

- PF
- expectancy
- drawdown
- sample size
- directional balance
- session stability
- unseen-period performance

No opaque self-modification.

## 19. Safety

- Gold/XAU enforcement
- no LIVE execution in V11 research build
- DEMO/Tester only if a real execution lane is enabled
- one-position policy for any real tester lane
- no martingale
- no grid recovery
- no external API dependency

## 20. Version Identity

V11 must print a unique build ID and embed unique magic numbers/telemetry filenames so the Strategy Tester report proves exactly which file was tested.

Required source name:

`AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`

Required banner example:

`AUREON Ω V11 ARC | build 20261005-01 | autonomous multi-lane research | zero-config`

## 21. Primary Benchmark

First validation run:

- XAUUSD
- M1
- Every tick based on real ticks
- 2026-01-01 through 2026-10-02
- $10,000 reference balance
- 1:100 leverage
- default inputs unchanged

The user should not manually tune any parameter before this benchmark.

## 22. Acceptance Criteria for Candidate 1

Candidate 1 succeeds if:

- it compiles cleanly
- all embedded lanes execute through the full benchmark period
- lane statistics are separated correctly
- final leaderboard is produced
- V2.17 control lane is measurable
- at least one lane produces a statistically useful sample, preferably >=100 trades
- no lane can silently contaminate another lane's state
- telemetry is sufficient to identify which feature families improve or degrade edge

Candidate 1 is not required to produce a profitable champion. Its purpose is to maximize research throughput and identify the shortest path back to a durable high-frequency edge.

## 23. Follow-up Research Sequence

After Candidate 1:

1. verify V2.17 control reproduction
2. identify top 3 lanes by robust ranking
3. run ablation on only those lanes
4. test unseen historical period
5. promote one champion
6. then test more aggressive compounding/scaling separately

## 24. Non-Goals

- no profit guarantees
- no acceptance based solely on million/billion headline profit
- no manual `.set` file dependency
- no external AI/API dependency for trade permission
- no LIVE deployment
- no martingale/grid
- no brute-force parameter optimizer embedded into Candidate 1

## 25. Decision

V11 changes the development workflow from sequential candidate patching to one autonomous multi-lane research pass. The first deliverable is a single zero-configuration `.mq5` that maximizes information gained per Strategy Tester run and restores the frozen V2.17 behavior as a control lane before further optimization.