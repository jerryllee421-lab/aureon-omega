# AUREON Ω HFS V2.1 — Improvement & Validation Design

Date: 2026-10-11
Branch: `research/hfs-v21-improvement-20261011`
Status: DESIGN FOR REVIEW

## 1. Objective

Improve the current AUREON Ω HFS / Profit Harvester design without mutating the frozen V2.12 historical control and without creating another version purely for headline backtest balance.

Primary objective: achieve robust positive expectancy on XAUUSD with high opportunity throughput, realistic execution costs, deterministic logic, and strict promotion gates.

Secondary objective: preserve the aggressive profit-harvest/recycle behavior while preventing low-quality entries and exit churn from dominating results.

LIVE execution remains blocked. Research and eventual broker-connected validation are DEMO-only until a separate explicit live authorization exists.

## 2. Current evidence

The latest successful GitHub Actions run, `HFS V2.1 Policy Tournament` (run 38084545714, commit `1e887c45783aaf87c2539edebe913f4d95c90ed2`), tested six causal policy variants against pinned 2016-2025 XAUUSD M1 bid/ask data.

The best development variant was `failure_v2`:

- Development 2016-2022: 634 trades, net -323.39 USD, win rate 40.85%, PF 0.614.
- Validation 2023-2025: 1,269 trades, net -1,130.35 USD, win rate 42.16%, PF 0.572.
- Full 2016-2025: 1,903 trades, net -1,453.74 USD, PF 0.582.

No tournament variant reached positive expectancy.

Additional artifact diagnostics:

- Median hold time is ~2 minutes for `failure_v2`.
- Entry score is heavily concentrated around 67, so the current score has weak discriminatory power.
- Losses are dominated by `FAILURE` exits and full `SL` exits.
- The bar-approx research lane is useful for causal screening but is not native MT5 real-tick parity evidence.
- 2023-2025 has already been inspected and must not be described as an untouched future holdout for subsequent model selection.

Conclusion: V2.1 is currently a rejected research candidate. The next work must repair the signal/economics architecture rather than tune the existing thresholds blindly.

## 3. Approaches considered

### A. Threshold tuning only

Raise entry score, change stop size, extend hold time, and tune profit-lock thresholds.

Pros: fast and cheap.

Cons: current score distribution is compressed, all tested variants are negative, and threshold search risks curve fitting.

Decision: reject as primary approach. Threshold tuning is allowed only after the score and state machine are made causally informative.

### B. Add more indicators

Add RSI, ADX, Stochastic, extra EMAs, more FVG/OB flags, and session filters directly into one large score.

Pros: more available features.

Cons: increases complexity, correlation, and overfit risk without fixing the existing scoring/economics problem.

Decision: reject as default architecture. New features must earn inclusion through ablation evidence.

### C. Causal state-machine rebuild inside V2.1 architecture — recommended

Keep the HFS V2.1 identity but replace the monolithic score/exit behavior with independently testable layers:

1. market regime/context;
2. setup trigger;
3. execution/economics gate;
4. position state;
5. profit-harvest/recycle policy.

Decision: recommended. This preserves the project direction while making each source of edge measurable and removable if it fails.

## 4. Research contract

### 4.1 Frozen controls

Do not mutate:

- `ea/baseline/FVG_Scalper_V2_12_Research.mq5`
- its canonical presets and recorded historical control evidence.

Existing HFS V2.1 artifacts remain reproducibility evidence, not a champion.

### 4.2 Data provenance

Every experiment must record:

- source repository and data commit/hash;
- code commit/hash;
- symbol specification assumptions;
- time range;
- bid/ask construction;
- commission, spread and slippage model;
- bar/tick fidelity;
- configuration hash.

### 4.3 Temporal split policy

Because 2023-2025 has already been examined, it is no longer an untouched final holdout.

Use:

- historical development/diagnostic data for iteration;
- rolling walk-forward splits inside the historical range;
- a genuinely new external holdout for final promotion, preferably 2026 PXBT/MT5 real-tick or broker-native history not used during feature/policy selection.

No candidate may be selected using final-holdout metrics.

## 5. Causality and data integrity

All decision features must be available before the entry decision.

Requirements:

- closed-candle features are shifted explicitly;
- current-bar high/low/close cannot influence an entry at that bar's open;
- higher-timeframe values use only closed higher-timeframe candles;
- bid/ask side is respected for entry, stop, target and exit calculations;
- no silent fallback from real ticks to generated ticks;
- invalid/missing broker symbol properties fail closed;
- spread and slippage are modeled separately;
- no fixed `POINT`, contract size, tick value or volume assumption in production parity code when broker metadata is available.

The Python research lane must include deterministic causality tests before strategy tests.

## 6. Signal architecture

### 6.1 Layer A — regime/context

Purpose: determine whether the market is structurally favorable for long, short, both, or neither.

Candidate context features, each independently ablatable:

- EMA100 / EMA200 location and slope;
- VWAP location and distance normalized by ATR;
- volatility regime;
- session/time-of-day regime;
- recent structural compression/expansion.

Context must not itself trigger a trade.

### 6.2 Layer B — setup trigger

Purpose: identify a discrete event worth entering.

Candidate triggers:

- liquidity sweep + reclaim;
- MSS / breakout-reclaim;
- displacement candle quality;
- FVG / IFVG formation and retracement;
- failure-to-continue reversal.

A trigger must have a unique event identity so the engine cannot repeatedly enter the same setup unless a new qualifying event occurs.

### 6.3 Layer C — economics gate

Purpose: reject trades that cannot realistically pay for execution and risk.

Required checks:

- spread-to-ATR ratio;
- expected target distance versus spread + commission + slippage;
- structural stop distance;
- maximum practical stop distance;
- minimum net reward/risk after costs;
- minimum expected excursion potential.

A high technical score cannot override impossible economics.

### 6.4 Layer D — entry quality score

Replace the current compressed additive score with a calibrated, interpretable score whose components are logged separately.

The score should reward independent evidence rather than duplicate correlated signals.

Mandatory telemetry per candidate event:

- context score;
- trigger score;
- economics score;
- buy evidence;
- sell evidence;
- contradictions;
- threshold used;
- rejection reason.

A score is promoted only if higher score bands show monotonic or at least materially improving expectancy during development/walk-forward analysis.

## 7. Position and exit state machine

States:

`NEW -> PROTECTED -> HARVEST -> RUNNER -> CLOSED`

with failure paths to `CLOSED` from any live state.

### NEW

Goal: validate immediate follow-through without panic-closing every temporary adverse move.

Use:

- structural invalidation / broker-side SL;
- minimum observation window where safe;
- explicit opposite-signal emergency exit only when opposition is materially stronger, not merely numerically higher.

### PROTECTED

Once price has covered estimated execution cost plus a safety margin, move protection only if the new stop is valid under broker stop/freeze rules.

### HARVEST

Capture small profitable moves when edge decays or retracement exceeds a calibrated fraction of MFE.

### RUNNER

Only exceptional setups qualify. Runner promotion must require evidence beyond entry score alone, for example persistent structure + favorable excursion + low opposition.

### CLOSED

Log a single authoritative close reason. Duplicate or stale close actions are prohibited.

## 8. Risk governor

Research defaults:

- no martingale;
- no grid;
- one-position / bounded campaign exposure during early parity work;
- daily loss governor;
- drawdown governor;
- consecutive-loss circuit breaker;
- broker margin and volume validation;
- fail closed on stale/invalid market data.

Risk sizing must be separated from signal quality. A strategy cannot be made profitable by increasing size.

## 9. Execution architecture

Order mutation must be serialized and idempotent.

Required execution invariants:

- one immutable trade intent ID per entry event;
- broker-authoritative open-position state;
- exactly-once logical close semantics;
- stale ticket / already-closed detection;
- reconnect reconciliation before new orders;
- stop/target mutation acknowledgment before local state transition;
- DEMO and LIVE environments explicitly distinguished;
- LIVE remains hard-blocked in research/certification workflows.

## 10. Test program

### Phase 0 — reproduce existing evidence

Re-run the existing HFS V2.1 tournament and verify artifact hashes/summary metrics.

### Phase 1 — unit/property tests

Test:

- feature causality;
- bid/ask side correctness;
- spread/slippage calculations;
- stop/target geometry;
- event uniqueness;
- state transitions;
- daily loss and drawdown governors;
- deterministic replay.

### Phase 2 — mechanism ablation

Test one mechanism at a time:

- context off/on;
- liquidity trigger off/on;
- MSS/structure off/on;
- displacement off/on;
- FVG/IFVG off/on;
- economics gate off/on;
- session regime off/on;
- adaptive exit off/on.

Do not optimize all parameters simultaneously.

### Phase 3 — policy tournament

Use development/walk-forward data only to select among a small predeclared policy set.

Candidate policy families:

1. precision: stricter trigger + strong economics;
2. balanced: moderate trigger + adaptive harvest;
3. high-throughput: permissive context but hard economics and rapid recycle.

### Phase 4 — robustness

Require:

- walk-forward stability;
- parameter-neighbor stability;
- spread stress;
- slippage stress;
- delayed-entry/exit stress;
- trade-order Monte Carlo / bootstrap;
- alternate broker/data-source comparison.

### Phase 5 — native MT5 parity

Compile with official MetaEditor at 0 errors / 0 warnings.

Run MT5 Strategy Tester with Every tick based on real ticks when available.

Verify representative trades candle/tick-by-tick against the research engine. Material divergence blocks promotion.

### Phase 6 — external final holdout

Use new 2026 broker-native data not used in research selection.

### Phase 7 — DEMO forward

Only candidates surviving all earlier gates may enter controlled DEMO forward validation.

## 11. Promotion gates

A candidate may not be called champion unless it satisfies all of the following:

- positive net expectancy after realistic costs;
- PF > 1.0 in development and repeated walk-forward windows, with a practical margin above break-even preferred;
- no single month/hour/side is responsible for the majority of profit;
- drawdown inside the configured governor;
- stable nearby parameters;
- acceptable spread/slippage stress;
- native MT5 parity verified;
- new external holdout remains positive;
- DEMO forward reconciliation passes.

Headline balance or trade count alone is never a promotion criterion.

## 12. First implementation slice after approval

The first code slice will not add indicators. It will:

1. create deterministic causality/economics tests for the existing HFS research engine;
2. refactor the entry decision into `context`, `trigger`, `economics`, and `quality` components while preserving current behavior under a compatibility mode;
3. add structured rejection/entry telemetry;
4. run the existing tournament as a regression control;
5. launch a small predeclared ablation tournament without reading the future external holdout.

This slice is complete only when tests pass and the baseline regression is reproducible.
