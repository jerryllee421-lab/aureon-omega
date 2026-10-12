# AUREON Ω V3 Profit Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a causal, research-first AUREON Ω V3 Profit Hunter that preserves immutable historical controls, tests specialist alpha and exit logic rigorously, and produces a single native-MT5 candidate only after research promotion gates pass.

**Architecture:** Extend the existing `research/` stack with a focused `research/v3_profit_hunter/` package instead of creating a parallel research system. Preserve V2.12/V2.17 historical controls, reuse the pinned XAUUSD mirror/data-gate/evolution infrastructure, run specialist and exit tournaments with rolling walk-forward/stress tests, then generate one challenger `.mq5` only from a machine-readable promoted contract. Native MetaEditor/MT5 real-tick evidence remains the final authority before any DEMO-forward integration.

**Tech Stack:** Python 3.13, pandas, NumPy, SciPy, PyArrow, PyYAML, pytest, GitHub Actions, MQL5/MetaEditor, existing Wine/MT5 CI compile lane.

**Spec:** `docs/superpowers/specs/2026-10-12-aureon-v3-profit-hunter-design.md`

## Global Constraints

- Market: XAUUSD / Gold only.
- Research period target: 2016-01-01 through 2025-12-31; this period is already inspected and must never be called untouched.
- Initial alpha research uses fixed 0.01-lot-equivalent exposure / R-space metrics; no compounding for edge validation.
- Existing V2.12 and imported V2.17 controls are immutable evidence and must never be mutated by challenger code.
- No martingale, grid recovery, loss-recovery sizing, hidden leverage escalation, or headline-balance promotion.
- Causal data only: no current/future completed-bar information may leak into an earlier decision timestamp.
- Bid/Ask execution semantics are mandatory; Python results remain labeled as research approximations until native MT5 real-tick parity passes.
- Fresh-event ID plus minimum 6-second anti-churn control remains mandatory after exits.
- Long and short policies are evaluated independently.
- Promotion requires positive OOS expectancy and OOS PF >= 1.0 at minimum; preferred V3 targets remain full-period PF >= 1.50, rolling walk-forward PF >= 1.25, stressed PF > 1.05, and max DD preferably below 10-12%.
- No automatic research → native → DEMO promotion.
- LIVE trading remains prohibited by this plan.

## Review Focus

1. **Causality leakage:** perturbing the current/future bar must not change any feature, regime, or setup decision already made from closed data.
2. **Bid/Ask and intrabar ambiguity:** simultaneous SL/TP touches must use conservative stop-first ordering in bar proxies; Ask must never fall below Bid without failing the data gate.
3. **Duplicate/fresh-event errors:** the same setup must not recycle after exit, while a genuinely new setup must not be falsely suppressed.
4. **Small-sample conditional EV:** regime/session/direction cohorts below the minimum sample must not create confident EV gates or promotion claims.
5. **Native execution geometry:** broker min volume/step, stop/freeze levels, partial-exit rounding, and DEMO-only account mode must fail closed rather than silently alter risk.

---

### Task 1: Freeze V2.17 Benchmark Provenance

**Files:**
- Create: `ea/baseline/FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5`
- Create: `research/baselines/fvg_v217_verified_2026.json`
- Create: `research/v3_profit_hunter/benchmark.py`
- Create: `research/tests/v3_profit_hunter/test_benchmark_freeze.py`

**Interfaces:**
- Produces: `load_benchmark(path: Path) -> BenchmarkRecord`
- Produces: `verify_file_sha256(path: Path, expected: str) -> bool`
- Benchmark exact recorded metrics: PF `2.48`, trades `18368`, WR `68.06`, equity DD `17.74`, short WR `72.86`, long WR `65.26`.

- [ ] **Step 1: Add failing benchmark-provenance tests** asserting exact metric values and SHA presence for the V2.17 source.
- [ ] **Step 2: Run** `python -m pytest research/tests/v3_profit_hunter/test_benchmark_freeze.py -q` and verify failure because the V2.17 repo baseline/manifest do not yet exist.
- [ ] **Step 3: Import the exact approved V2.17 source artifact** into `ea/baseline/` without reconstruction from memory; compute SHA-256 and write `fvg_v217_verified_2026.json` with evidence metadata and `immutable_control: true`.
- [ ] **Step 4: Implement `BenchmarkRecord`, `load_benchmark`, and `verify_file_sha256`** in `benchmark.py`.
- [ ] **Step 5: Re-run the benchmark tests** and require PASS.
- [ ] **Step 6: Commit** `test: freeze V2.17 benchmark provenance`.

### Task 2: Create V3 Package, Data Contract, and Causality Guard

**Files:**
- Create: `research/v3_profit_hunter/__init__.py`
- Create: `research/v3_profit_hunter/models.py`
- Create: `research/v3_profit_hunter/data_contract.py`
- Modify: `research/requirements.txt`
- Create: `research/tests/v3_profit_hunter/test_data_contract.py`
- Create: `research/tests/v3_profit_hunter/test_causality.py`

**Interfaces:**
- `validate_market_frame(df: pd.DataFrame) -> DataQualityReport`
- `decision_view(df: pd.DataFrame, decision_i: int) -> MarketContext`
- `DataFidelity = Literal["BID_ASK_M1_BAR_PROXY", "NATIVE_MT5_REAL_TICKS"]`
- `MarketContext` exposes only data legally available at the decision timestamp.

- [ ] **Step 1: Add `pytest>=8,<9`** to `research/requirements.txt`.
- [ ] **Step 2: Write failing tests** for required columns, monotonic UTC time, duplicate timestamps, Ask >= Bid, non-negative spreads, valid OHLC, and causal closed-bar visibility.
- [ ] **Step 3: Add the key causality regression:** mutate bar `i` and all bars after `i`; assert features/context for a decision based on bars through `i-1` remain identical.
- [ ] **Step 4: Implement dataclasses/enums** for `DataQualityReport`, `MarketContext`, `Direction`, `CandidateState`, and `DataFidelity`.
- [ ] **Step 5: Implement `validate_market_frame` and `decision_view`** using the canonical schema already produced by `mirror_m1.py` / `resample_validate.py`.
- [ ] **Step 6: Run** `python -m pytest research/tests/v3_profit_hunter/test_data_contract.py research/tests/v3_profit_hunter/test_causality.py -q` and require PASS.
- [ ] **Step 7: Commit** `feat: add V3 causal market-data contract`.

### Task 3: Feature Factory and Regime Brain

**Files:**
- Create: `research/v3_profit_hunter/features.py`
- Create: `research/v3_profit_hunter/regimes.py`
- Create: `research/v3_profit_hunter/config/base.yml`
- Create: `research/tests/v3_profit_hunter/test_features.py`
- Create: `research/tests/v3_profit_hunter/test_regimes.py`

**Interfaces:**
- `prepare_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame`
- `classify_regime(row: pd.Series, cfg: RegimeConfig) -> Regime`
- Regimes: `TREND_EXPANSION`, `TREND_PULLBACK`, `BREAKOUT_TRANSITION`, `VOLATILITY_COMPRESSION`, `VOLATILITY_EXPANSION`, `RANGE`, `LIQUIDITY_REVERSAL`, `EXHAUSTION`, `CHAOTIC`, `TOXIC_EXECUTION`, `UNKNOWN_DEGRADED`.

- [ ] **Step 1: Write failing synthetic-fixture tests** for ATR percentile, EMA20/50/100/200 context, displacement/body efficiency, prior liquidity levels, session VWAP where volume exists, rolling micro-VWAP, spread/ATR, FVG geometry, MSS/BOS flags, and session labels.
- [ ] **Step 2: Add leakage tests** proving every entry-time feature is shifted/closed correctly.
- [ ] **Step 3: Implement `prepare_features`** with deterministic timestamp alignment and explicit missing-data handling.
- [ ] **Step 4: Write regime fixture tests** for trend, range, liquidity reversal, compression/expansion, toxic spread, and degraded inputs.
- [ ] **Step 5: Implement `classify_regime`** as routing/ranking only; no hard strategy block unless config explicitly enables a research-tested gate.
- [ ] **Step 6: Run feature/regime tests** and require PASS.
- [ ] **Step 7: Commit** `feat: add V3 feature factory and regime brain`.

### Task 4: Specialist Contract and V2.17 Heritage Control

**Files:**
- Create: `research/v3_profit_hunter/specialists/__init__.py`
- Create: `research/v3_profit_hunter/specialists/base.py`
- Create: `research/v3_profit_hunter/specialists/fvg_heritage.py`
- Create: `research/tests/v3_profit_hunter/test_fvg_heritage.py`

**Interfaces:**
- `Specialist.detect(ctx: MarketContext) -> SetupCandidate | None`
- `SetupCandidate` includes specialist ID, direction, setup timestamp, event identity inputs, zone geometry, invalidation, trigger, quality fields, regime, and data fidelity.
- Specialist ID: `V217_FVG_HERITAGE`.

- [ ] **Step 1: Write failing synthetic FVG tests** covering bullish/bearish three-bar gap formation, displacement minimum, body ratio, rejection, zone invalidation, zone age, and repeated-zone behavior.
- [ ] **Step 2: Implement the specialist protocol and `SetupCandidate` contract**.
- [ ] **Step 3: Implement V2.17 heritage detection** preserving FVG/displacement/rejection semantics while leaving 30R, zero cooldown, and unlimited re-entry as testable policies rather than hard-coded truths.
- [ ] **Step 4: Add parity fixtures** against equivalent control cases from `research/fvg_v211.py`; assert identical direction/zone/invalidation on the fixtures.
- [ ] **Step 5: Run** `python -m pytest research/tests/v3_profit_hunter/test_fvg_heritage.py -q` and require PASS.
- [ ] **Step 6: Commit** `feat: add V2.17 heritage specialist`.

### Task 5: Challenger Specialists

**Files:**
- Create: `research/v3_profit_hunter/specialists/ifvg.py`
- Create: `research/v3_profit_hunter/specialists/liquidity_mss.py`
- Create: `research/v3_profit_hunter/specialists/momentum.py`
- Create: `research/v3_profit_hunter/specialists/trend_pullback.py`
- Create: `research/tests/v3_profit_hunter/test_specialists.py`

**Interfaces:**
- IDs: `IFVG_FLIP`, `LIQUIDITY_SWEEP_MSS`, `MOMENTUM_EXPANSION`, `TREND_PULLBACK`.
- Every specialist implements the same `detect(ctx)` contract and remains separately attributable.

- [ ] **Step 1: Write failing iFVG tests** for FVG formation → violation/close-through → role flip → retest/rejection.
- [ ] **Step 2: Implement iFVG specialist**.
- [ ] **Step 3: Write failing liquidity tests** requiring pool → sweep → reclaim → MSS/BOS → displacement → retracement; assert sweep-only setups do not complete.
- [ ] **Step 4: Implement liquidity/MSS specialist**.
- [ ] **Step 5: Write failing momentum tests** for compression → expansion → displacement → target room.
- [ ] **Step 6: Implement momentum specialist**.
- [ ] **Step 7: Write failing trend-pullback tests** for causal trend → value/FVG pullback → countertrend decay → resumption.
- [ ] **Step 8: Implement trend-pullback specialist**.
- [ ] **Step 9: Run all specialist tests** and require PASS.
- [ ] **Step 10: Commit** `feat: add V3 alpha challengers`.

### Task 6: Event Identity, Entry State Machine, Anti-Churn, and Cost/EV Gate

**Files:**
- Create: `research/v3_profit_hunter/entry.py`
- Create: `research/v3_profit_hunter/economics.py`
- Create: `research/tests/v3_profit_hunter/test_entry_state.py`
- Create: `research/tests/v3_profit_hunter/test_economics.py`

**Interfaces:**
- `make_event_id(candidate: SetupCandidate) -> str`
- `EntryStateMachine.advance(candidate, observation) -> CandidateState`
- `CostModel.estimate(entry_price, spread, commission, slippage, size) -> CostEstimate`
- `CohortEV.fit(training_trades: pd.DataFrame) -> CohortEV`
- `CohortEV.evaluate(candidate) -> EVDecision`
- Minimum conditional cohort sample: `50`; below that, label `INSUFFICIENT_SAMPLE` and fall back only to deterministic post-cost target-room research, never a confident learned-EV claim.

- [ ] **Step 1: Write event-ID tests** proving identical setup identity is stable and genuinely new formation/zone/direction produces a new ID.
- [ ] **Step 2: Write state-machine tests** for `DETECTED → DEVELOPING → ARMED → TRIGGERED → CONFIRMED → EXECUTED` plus invalidated/expired/cost-blocked/duplicate-blocked terminals.
- [ ] **Step 3: Add anti-churn regression tests** requiring >=6 seconds after close **and** a fresh event; prove time alone cannot recycle the closed setup.
- [ ] **Step 4: Implement event identity and state machine**.
- [ ] **Step 5: Write cost tests** for spread, commission, slippage, and negative post-cost room.
- [ ] **Step 6: Write EV tests** ensuring holdout rows are never used in `fit`, low samples return `INSUFFICIENT_SAMPLE`, and long/short/regime/session cohorts are separable.
- [ ] **Step 7: Implement cost/EV gate**.
- [ ] **Step 8: Run entry/economics tests** and require PASS.
- [ ] **Step 9: Commit** `feat: add causal entry and post-cost EV gates`.

### Task 7: Profit Hunter Position Manager and Excursion Intelligence

**Files:**
- Create: `research/v3_profit_hunter/position.py`
- Create: `research/v3_profit_hunter/excursions.py`
- Create: `research/tests/v3_profit_hunter/test_position_manager.py`
- Create: `research/tests/v3_profit_hunter/test_excursions.py`

**Interfaces:**
- `PositionManager.on_bar(position, bar, signals) -> PositionDecision`
- States: `MICRO`, `STANDARD`, `RUNNER`, `PROTECT`, `EXIT_PENDING`.
- `update_excursions(position, bar) -> ExcursionState`
- `profit_capture_ratio(realized_favorable: float, mfe: float) -> float | None`

- [ ] **Step 1: Write failing MFE/MAE tests** including time-to-0.25R/0.5R/1R/1.5R/2R/3R and post-peak giveback.
- [ ] **Step 2: Implement excursion tracking and PCR**.
- [ ] **Step 3: Write failing state-transition tests** proving transitions are monotonic except explicit `→ PROTECT`, stops never widen, and cost-covered break-even cannot increase risk.
- [ ] **Step 4: Add target-family tests** for fixed-R, ATR, liquidity target, staged TP1/TP2/TP3, and runner policies.
- [ ] **Step 5: Implement position manager** with strategy-aware exit policy hooks.
- [ ] **Step 6: Run position/excursion tests** and require PASS.
- [ ] **Step 7: Commit** `feat: add Profit Hunter position manager`.

### Task 8: Causal Simulator, Ledger, Metrics, and Failure Attribution

**Files:**
- Create: `research/v3_profit_hunter/simulator.py`
- Create: `research/v3_profit_hunter/metrics.py`
- Create: `research/v3_profit_hunter/ledger.py`
- Create: `research/v3_profit_hunter/failure_attribution.py`
- Create: `research/tests/v3_profit_hunter/test_simulator.py`
- Create: `research/tests/v3_profit_hunter/test_metrics.py`

**Interfaces:**
- `simulate(frame, specialists, policy, execution_model) -> SimulationResult`
- `summarize(trades: pd.DataFrame) -> MetricsReport`
- `write_ledger(trades, path, experiment_id) -> Path`
- `classify_failure(trade, context) -> FailureClass`

- [ ] **Step 1: Write bid/ask simulator tests** proving long exits use Bid, short exits use Ask, spread is charged correctly, and simultaneous stop/TP bar touches resolve stop-first.
- [ ] **Step 2: Implement sequential simulator** with no same-bar future leakage; any intrabar-bar proxy must be labeled and use conservative sequencing.
- [ ] **Step 3: Write metric tests** for PF, expectancy R, max DD R/%, recovery, WR, payoff, direction/year/session/regime breakdowns, and PCR.
- [ ] **Step 4: Implement metrics and append-only experiment ledger** with code SHA, dataset SHA, data fidelity, config SHA, and experiment ID.
- [ ] **Step 5: Write failure-attribution tests** for never-positive-MFE, late entry, false breakout, wrong regime, adverse cost, insufficient displacement, failed reclaim, poor stop geometry, premature failure exit, structural invalidation, and unknown.
- [ ] **Step 6: Implement failure attribution**.
- [ ] **Step 7: Run simulator/metrics tests** and require PASS.
- [ ] **Step 8: Commit** `feat: add V3 simulator and evidence ledger`.

### Task 9: Alpha Tournament, Exit Tournament, and Rolling Walk-Forward

**Files:**
- Create: `research/v3_profit_hunter/tournament.py`
- Create: `research/v3_profit_hunter/walkforward.py`
- Create: `research/v3_profit_hunter/config/tournament.yml`
- Create: `research/tests/v3_profit_hunter/test_tournament.py`
- Create: `research/tests/v3_profit_hunter/test_walkforward.py`

**Interfaces:**
- `run_alpha_tournament(...) -> TournamentReport`
- `run_exit_tournament(...) -> TournamentReport`
- `rolling_windows() -> list[WalkForwardWindow]` exactly covering train-through-2018/test-2019 through train-through-2024/test-2025.

- [ ] **Step 1: Write tournament tests** requiring each specialist and long-only/short-only variant to remain separately attributable.
- [ ] **Step 2: Implement Alpha Tournament** including V2.17 control, protected V2.17, FVG+displacement, FVG+MSS, FVG+liquidity, iFVG, liquidity+MSS, momentum, trend pullback.
- [ ] **Step 3: Write walk-forward tests** proving a test year is never present in training/selection data and no 2023-2025 data leaks into an earlier selection decision.
- [ ] **Step 4: Implement rolling walk-forward evaluator** and quarterly diagnostics where sample size permits.
- [ ] **Step 5: Implement hard rejection** for persistent negative OOS expectancy or OOS PF <1.0.
- [ ] **Step 6: Implement Exit Tournament** only for alpha survivors; compare original heritage locks, fixed-R, staged targets, MFE-derived targets, ATR trail, structure trail, momentum decay, hybrid Profit Hunter.
- [ ] **Step 7: Run tournament/walk-forward tests** and require PASS.
- [ ] **Step 8: Commit** `feat: add V3 alpha and exit tournaments`.

### Task 10: Robustness, Placebo, Parameter Stability, and Monte Carlo

**Files:**
- Create: `research/v3_profit_hunter/robustness.py`
- Create: `research/v3_profit_hunter/monte_carlo.py`
- Create: `research/v3_profit_hunter/promotion.py`
- Create: `research/evolution/v3_profit_hunter_policy.yml`
- Create: `research/tests/v3_profit_hunter/test_robustness.py`
- Create: `research/tests/v3_profit_hunter/test_promotion.py`

**Interfaces:**
- `run_cost_stress(candidate, scenarios) -> StressReport`
- `run_placebos(candidate, seed) -> PlaceboReport`
- `run_parameter_neighbors(candidate, deltas=(0.05,0.10,0.20)) -> StabilityReport`
- `monte_carlo(rs, paths=2000, seed=26081112, ...) -> MonteCarloReport`
- `classify_promotion(evidence) -> PromotionVerdict`

- [ ] **Step 1: Write stress tests** for 1.25x/1.5x/2x spread, 2x/3x slippage, higher commission, delayed entry, missed fills 5/10/20%.
- [ ] **Step 2: Implement deterministic stress runner** with fixed random seed for missed-fill/adverse-tail experiments.
- [ ] **Step 3: Write placebo tests** for inverted direction, randomized equal-count signals, shuffled-time, delayed-entry, feature ablation, and specialist ablation.
- [ ] **Step 4: Implement placebo/ablation and ±5/10/20% neighbor stability**.
- [ ] **Step 5: Implement Monte Carlo sequence/bootstrap analysis** with 95%/99% DD and ruin outputs.
- [ ] **Step 6: Write promotion tests** proving no candidate with OOS PF <1.0, negative OOS expectancy, causality failure, cost collapse, parameter cliff, or missing native gate can return a production-ready state.
- [ ] **Step 7: Implement V3 promotion policy** with preferred research targets from the spec and statuses `REJECTED`, `RESEARCH_PASS`, `PROMOTE_TO_NATIVE`.
- [ ] **Step 8: Run robustness/promotion tests** and require PASS.
- [ ] **Step 9: Commit** `feat: add V3 robustness and promotion gates`.

### Task 11: Research CLI and Free GitHub Actions Campaign

**Files:**
- Create: `research/v3_profit_hunter/cli.py`
- Create: `.github/workflows/v3-profit-hunter-research.yml`
- Modify: `.gitignore`
- Create: `research/tests/v3_profit_hunter/test_cli.py`

**Interfaces:**
- CLI subcommands: `validate-data`, `alpha`, `exits`, `walkforward`, `stress`, `promote`, `full-campaign`.
- Default dataset mirror commit: `922f83a60cc574e7395fb27397077288055a1ef6`.
- Full campaign range: `2016-01-01` through `2025-12-31`.

- [ ] **Step 1: Write CLI tests** requiring explicit experiment ID, config path, output path, and immutable provenance in every report.
- [ ] **Step 2: Implement CLI orchestration** without duplicating research logic.
- [ ] **Step 3: Add `.gitignore` entries** for `research_data/`, `research_results/`, and local V3 artifacts while keeping manifests/configs committed.
- [ ] **Step 4: Create GitHub workflow** using Ubuntu runner, Python 3.13, `research/requirements.txt`, pinned mirror import, `gold_data_gate.py`, resample validation, full V3 tests, then `full-campaign`.
- [ ] **Step 5: Workflow must upload** dataset manifest, source/config SHAs, baseline comparison, tournament outputs, ledgers, walk-forward report, stress report, Monte Carlo report, and promotion verdict.
- [ ] **Step 6: Run local syntax/tests:** `python -m compileall research/v3_profit_hunter research/tests/v3_profit_hunter` and `python -m pytest research/tests/v3_profit_hunter -q`.
- [ ] **Step 7: Commit** `ci: add V3 Profit Hunter research campaign`.

### Task 12: Produce a Selected Strategy Contract — Only on Research Promotion

**Files:**
- Create: `research/v3_profit_hunter/selected_contract.py`
- Generated after a passing campaign: `research/evolution/decisions/v3_profit_hunter_selected.json`
- Create: `research/tests/v3_profit_hunter/test_selected_contract.py`

**Interfaces:**
- `build_selected_contract(promotion_artifact, campaign_artifacts) -> SelectedStrategyContract`
- Contract must pin specialist IDs, direction-specific parameters, entry semantics, stop/target policies, anti-churn, cost assumptions, dataset/code hashes, and promotion evidence hashes.

- [ ] **Step 1: Write a failing test** proving contract generation rejects any verdict other than `PROMOTE_TO_NATIVE`.
- [ ] **Step 2: Add tests** proving selected parameters come only from promoted evidence and cannot be silently substituted.
- [ ] **Step 3: Implement selected-contract generation** and SHA-256 fingerprinting.
- [ ] **Step 4: Run selected-contract tests** and require PASS.
- [ ] **Step 5: Commit** `feat: freeze promoted V3 strategy contract`.

### Task 13: Single-File MQL5 Challenger and Native Certification Lane

**Files:**
- Create conditionally after Task 12 promotion: `ea/challengers/AUREON_OMEGA_V3_PROFIT_HUNTER.mq5`
- Create: `ea/challengers/v3-profit-hunter/README.md`
- Create: `ea/challengers/v3-profit-hunter/tester/V3_PROFIT_HUNTER.ini`
- Create: `research/v3_profit_hunter/native_parity.py`
- Create: `research/tests/v3_profit_hunter/test_native_contract.py`
- Modify: `scripts/mt5_linux_compile.sh`
- Create: `.github/workflows/v3-profit-hunter-native.yml`

**Interfaces:**
- The `.mq5` must be a single self-contained production-candidate source with no manual strategy inputs required for the certified configuration.
- `native_parity.compare(research_ledger, mt5_ledger) -> ParityReport`.
- Compile script accepts `EA_SOURCE` environment variable while retaining its current default for legacy baseline smoke tests.

- [ ] **Step 1: Write native-contract tests** proving no `.mq5` is generated without a valid selected contract and that the selected-contract fingerprint is embedded in the candidate.
- [ ] **Step 2: Implement the single-file EA** from the selected contract only; preserve broker SL/TP, event ID, anti-churn, research telemetry, long/short specialization, and fail-closed market checks.
- [ ] **Step 3: Add DEMO-only hard block** so a real/live MT5 account cannot place orders; native tester operation remains permitted.
- [ ] **Step 4: Add broker geometry handling** for min/max/step volume, stop/freeze levels, and partial-exit rounding; if the certified partial size is impossible, fail/convert according to an explicitly logged contract rule rather than silently changing risk.
- [ ] **Step 5: Parameterize `scripts/mt5_linux_compile.sh`** with `EA_SOURCE` and verify the legacy default remains `ea/baseline/FVG_Scalper_V2_11_ORIGINAL.mq5`.
- [ ] **Step 6: Create native workflow** to compile with official MetaEditor under Wine, require 0 errors, capture warnings, EX5/source hashes, and upload evidence.
- [ ] **Step 7: Configure Strategy Tester evidence path** using XAUUSD, `Every tick based on real ticks` where actual broker history is available, USD 10,000 research deposit, and DEMO account context only. Missing broker real ticks must produce `DATA_INCOMPLETE`, never a silent fallback.
- [ ] **Step 8: Implement parity comparison** for candidate identity, direction, entry/SL/TP geometry, event IDs, exit reasons, and aggregate PF/expectancy/trade-count drift.
- [ ] **Step 9: Run all Python contract tests**, run MetaEditor compile, then run native real-tick certification. Do not claim native certification without the actual compile/test artifacts.
- [ ] **Step 10: Commit** `feat: add native-certified V3 Profit Hunter challenger` only if gates pass; otherwise commit evidence/status as `RESEARCH_ONLY` without promotion.

---

## Final Verification Before Completion

Run fresh, in this order:

```bash
python -m compileall research/v3_profit_hunter research/tests/v3_profit_hunter
python -m pytest research/tests/v3_profit_hunter -q
python research/v3_profit_hunter/cli.py full-campaign \
  --config research/v3_profit_hunter/config/tournament.yml \
  --data research_data/XAUUSD/canonical/XAUUSD_M1.parquet \
  --out research_results/v3_profit_hunter/final \
  --experiment-id v3-final-verification
```

Then inspect the generated promotion verdict. Only if it is `PROMOTE_TO_NATIVE`, continue to MetaEditor/native MT5 verification. Require:

- data quality PASS;
- causality tests PASS;
- all V3 unit/contract tests PASS;
- control hashes unchanged;
- OOS expectancy positive;
- OOS PF >=1.0 minimum;
- robustness/placebo/parameter-stability evidence present;
- selected contract hash present;
- MetaEditor compile evidence present with 0 errors;
- native real-tick report present or explicit `DATA_INCOMPLETE`;
- LIVE trading still blocked.

## Deferred Independent Subsystem

The **20 → 50 → 100 → 250 → 500 DEMO-forward ladder** is intentionally not implemented in this plan. After a V3 candidate passes native real-tick certification, create a separate DEMO-forward integration specification/plan that reuses existing risk-governor/reconciliation infrastructure. This prevents a research-only candidate from accidentally acquiring broker-execution authority.
