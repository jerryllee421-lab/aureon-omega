# AUREON Ω V10 — HYBRID CHAMPION Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5` by combining the V2.17 M1 FVG alpha engine with the V9.7 intelligence/risk shell while preserving aggressive opportunity capture and adding explicit attribution, directional scoring, and fail-closed DEMO safety.

**Architecture:** V2.17 remains the alpha reference and supplies M1 FVG discovery, rejection/retest, repeat-entry capability, execution hardening, staged locks, ATR trailing and forward telemetry. V9.7 supplies the risk governor, VWAP/profile context, liquidity/structure features, MFE tracking, evidence logging and state discipline. V10 separates alpha generation from intelligence scoring so optional context ranks or sizes candidates instead of suppressing trade flow.

**Tech Stack:** MQL5 / MetaTrader 5, `CTrade`, MT5 Strategy Tester with Every tick based on real ticks, CSV telemetry, GitHub branch `feature/v10-hyper-scalper-intelligence`.

**Spec:** `docs/superpowers/specs/2026-10-05-aureon-v10-hybrid-champion-design.md`

## Global Constraints

- Primary market: XAUUSD / Gold.
- Primary execution timeframe: M1.
- LIVE trading remains prohibited for this research candidate; DEMO/research only.
- Preserve `FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5` and `AUREON_OMEGA_V9_7_SUPER_SCALPER_EDGE_REPAIR.mq5` unchanged as frozen references.
- No martingale, no grid recovery, no opaque self-modifying parameters.
- Intelligence features must rank, size or downgrade opportunities before they block them; only safety, invalidation or execution-integrity conditions may hard-block.
- Risk governor must apply in Strategy Tester.
- Hard blocks include stale tick, invalid broker spec, invalid normalized volume, invalid stop/freeze geometry, excessive spread/slippage, insufficient margin, duplicate state, unresolved reconciliation mismatch, daily-loss breach, drawdown breach, LIVE account, and explicit FVG invalidation.
- First benchmark is research evidence, not a profit guarantee.

## Review Focus

1. **Repeated FVG entries:** verify second and later entries remain possible when the FVG is still valid, but telemetry increments `entry_no_on_fvg` correctly and duplicate live positions are not created.
2. **Directional asymmetry:** verify long and short thresholds are evaluated independently and telemetry records the threshold actually used.
3. **Optional-context failure:** unavailable VWAP/profile/EMA100/AMD data must reduce score confidence, not silently fabricate values or hard-block a valid FVG.
4. **Risk fail-closed behavior:** daily-loss/drawdown/LIVE-account violations must prevent new entries and preserve evidence of the reason.
5. **Exit interaction:** staged locks, ATR trail and MFE protection must not loosen an existing stop or double-close the same managed position.

---

### Task 1: Create the V10 source shell and frozen regression harness

**Files:**
- Create: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Create: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: frozen reference behavior from `FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5` and `AUREON_OMEGA_V9_7_SUPER_SCALPER_EDGE_REPAIR.mq5`.
- Produces: V10 source namespace, version metadata, research-only mode guards, and static regression assertions used by later tasks.

- [ ] **Step 1: Write the failing source-regression test**

Assert that the V10 file exists and contains: `#property version`, `PERIOD_M1`, an explicit LIVE hard block token/function, Strategy Tester risk-governor applicability, and V10-specific telemetry filenames.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python tests/v10_source_regression.py`
Expected: FAIL because the V10 file does not yet exist.

- [ ] **Step 3: Create the minimal V10 shell**

Add version header, imports, enums/struct placeholders, research/DEMO mode inputs, Gold enforcement, state globals and telemetry filenames. Do not yet port strategy logic.

- [ ] **Step 4: Run the source-regression test**

Run: `python tests/v10_source_regression.py`
Expected: PASS for shell assertions.

- [ ] **Step 5: Commit**

`git commit -am "feat: scaffold AUREON V10 hybrid champion"`

### Task 2: Port the V2.17 M1 FVG alpha engine

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: V10 shell.
- Produces: `FVGZone`, FVG discovery, invalidation, rejection/retest, entry eligibility, FVG id generation, repeat-entry state.

- [ ] **Step 1: Add failing assertions for V2.17 alpha invariants**

Assert M1 entry timeframe, `InpOneTradePerFVG=false` equivalent behavior, FVG width/body thresholds, FVG persistence/replacement, rejection confirmation, and per-FVG entry counter.

- [ ] **Step 2: Run test and verify failure**

Run: `python tests/v10_source_regression.py`
Expected: FAIL on missing alpha invariants.

- [ ] **Step 3: Port the minimal V2.17 alpha path**

Implement V2.17-equivalent FVG discovery/rejection/retest behavior in V10 names. Preserve repeated-entry capability and avoid importing V9.x hard filters.

- [ ] **Step 4: Run regression test**

Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "feat: port V2.17 FVG alpha core into V10"`

### Task 3: Add explicit FVG / IFVG lifecycle and repeat-entry attribution

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: V2.17-derived FVG zone.
- Produces: `ENUM_V10_FVG_STATE`, `ClassifyFVGState(...)`, `entry_no_on_fvg`, previous outcome in R, and FVG lifecycle telemetry.

- [ ] **Step 1: Add failing tests for lifecycle states**

Assert source contains the states `FVG_FRESH`, `FVG_PARTIALLY_MITIGATED`, `FVG_FULLY_MITIGATED`, `IFVG_BULLISH`, `IFVG_BEARISH`, `FVG_INVALID` and explicit telemetry fields for FVG state + entry number.

- [ ] **Step 2: Run test and verify failure**

- [ ] **Step 3: Implement lifecycle classifier and state persistence**

Use only closed/current market data available at decision time. Track formation time, bounds, midpoint, age, entries, last exit time and last realized R.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add V10 FVG and IFVG lifecycle attribution"`

### Task 4: Port V9.7 risk governor and DEMO/LIVE execution guards

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: account equity, peak equity, UTC trading day, account mode, symbol and broker execution constraints.
- Produces: `UpdateV10RiskGovernor()`, `V10ExecutionAllowed(...)`, fail-closed reason codes.

- [ ] **Step 1: Add failing safety assertions**

Assert tester governor is enabled, LIVE mode is hard-blocked, XAU enforcement exists, daily-loss and equity-DD gates exist, and stale-tick/spread/slippage checks are wired into preflight.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Port governor and account guards**

Preserve V9.7 daily-loss reset semantics and peak-equity drawdown semantics. Keep explicit emergency halt state and evidence logging.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: port V9.7 risk governor into V10"`

### Task 5: Add VWAP / volume-profile intelligence as score-only context

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: M1/M5 price-volume data.
- Produces: `V10VolumeContext` with daily VWAP, London VWAP, anchored VWAP, slope, POC, VAL, VAH, value-area state, validity and score contribution.

- [ ] **Step 1: Add failing assertions for context fields and validity flags**

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Port V9.7 VWAP/profile calculations**

Ensure missing real volume or insufficient bars marks the relevant field invalid and lowers score contribution rather than blocking the candidate.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add VWAP and profile scoring to V10"`

### Task 6: Add liquidity / structure scoring

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: recent swing structure, prior-day high/low, Asia range, M5 structure and M1 sequence data.
- Produces: `V10StructureContext`, directional liquidity-sweep score, MSS/BOS flags and score contribution.

- [ ] **Step 1: Add failing assertions for sweep, MSS/BOS and location features**

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Port/adapt structure features from V9.7**

Do not make prior-day, Asia, swing or fib confluence mandatory in base research mode.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add liquidity and structure scoring to V10"`

### Task 7: Add EMA100 / regime and AMD scoring

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: M15/H1 price structure and EMA100; local accumulation/manipulation/distribution evidence.
- Produces: `V10RegimeContext`, `ENUM_V10_AMD_STATE`, AMD confidence and independent score contributions.

- [ ] **Step 1: Add failing assertions for EMA100 and AMD states**

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement minimal deterministic classifiers**

EMA100/regime uses price side + slope with validity flags. AMD returns accumulation, manipulation, distribution or unknown with a confidence scalar; unknown contributes zero rather than blocking.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add EMA100 regime and AMD scoring"`

### Task 8: Implement asymmetric long/short scoring and A+/A/B grading

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: alpha, volume, structure, regime and AMD contexts.
- Produces: `V10Decision BuildV10Decision(...)` with raw alpha score, intelligence score, direction threshold, grade, risk multiplier and reason.

- [ ] **Step 1: Add failing assertions for independent long/short thresholds**

Assert distinct inputs such as `InpLongTriggerScore` and `InpShortTriggerScore`, plus A+/A/B grade thresholds and grade-specific risk multipliers.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement deterministic weighted scoring**

Core FVG/rejection quality dominates. Optional context contributes bounded positive/negative modifiers. Hard blocking remains restricted to the Global Constraints list.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add asymmetric V10 scoring and setup grades"`

### Task 9: Merge execution hardening and normalized order placement

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: `V10Decision`, symbol spec, tick, risk governor state.
- Produces: normalized volume, validated SL/TP, transient-retry execution, requested/actual entry and slippage evidence.

- [ ] **Step 1: Add failing assertions for broker stop/freeze checks, transient retry and post-fill verification**

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Port V2.17 execution hardening**

Retain symbol-based filling, transient-only retries, position verification and broker stop/freeze rejection.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: harden V10 order execution"`

### Task 10: Merge staged locks, ATR trail and restrained MFE protection

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: managed-position state, entry risk distance, live MFE/MAE.
- Produces: monotonic SL management, exit reason attribution and realized-R tracking.

- [ ] **Step 1: Add failing assertions for Lock1, Lock2, 0.10 ATR baseline trail and MFE overlay**

Also assert that the MFE overlay is disabled or subordinate until minimum favorable excursion is reached.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement combined position manager**

Start from V2.17 lock/trail behavior. Add MFE giveback only after its arm threshold and never allow it to loosen the current SL. Keep stagnation lenient/off by default.

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: add V10 hybrid profit manager"`

### Task 11: Complete attribution telemetry and dashboard

**Files:**
- Modify: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`
- Modify: `tests/v10_source_regression.py`

**Interfaces:**
- Consumes: all decision/execution/position state.
- Produces: `AUREON_V10_FORWARD.csv`, `AUREON_V10_SIGNALS.csv`, `AUREON_V10_TRADES.csv`, dashboard status.

- [ ] **Step 1: Add failing telemetry-schema assertions**

Require timestamp, side, FVG id/state, entry number, grade, alpha score, intelligence score, threshold, IFVG state, VWAP/profile values, EMA100/regime, AMD/confidence, spread/slippage, MFE/MAE, realized R, exit reason, cumulative WR/PF and account DD.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement complete telemetry and dashboard**

- [ ] **Step 4: Run regression test**

- [ ] **Step 5: Commit**

`git commit -am "feat: complete V10 attribution telemetry"`

### Task 12: Static verification and Strategy Tester handoff

**Files:**
- Modify: `tests/v10_source_regression.py` only if verification exposes missing invariants.
- Produce: `mt5/AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5`

**Interfaces:**
- Consumes: completed V10 source.
- Produces: verified source artifact ready for native MetaEditor compile and first real-tick benchmark.

- [ ] **Step 1: Run the full static regression suite**

Run: `python tests/v10_source_regression.py`
Expected: PASS, 0 failed assertions.

- [ ] **Step 2: Run structural sanity checks**

Check balanced braces/brackets/parentheses, duplicate function names, placeholder/TODO markers, and accidental `LIVE` enablement.

- [ ] **Step 3: Verify frozen references are unchanged**

Compare checksums or Git diff for V2.17 and V9.7 reference files.

- [ ] **Step 4: Commit final source candidate**

`git commit -am "feat: complete AUREON V10 hybrid champion candidate"`

- [ ] **Step 5: Native compile gate**

Open `AUREON_OMEGA_V10_HYBRID_CHAMPION.mq5` in MetaEditor and compile.
Expected: 0 errors; review/resolve warnings where practical.

- [ ] **Step 6: Primary benchmark**

MT5 Strategy Tester: XAUUSD, M1, Every tick based on real ticks, same broker/data environment, $10,000, 1:100, optimization OFF.

Record: total trades, PF, WR, expectancy, Sharpe, max relative equity DD, average hold, long PF/WR, short PF/WR, first-entry PF, repeat-entry PF by entry number.

- [ ] **Step 7: Run ablation sequence**

Benchmark in order: core only; +VWAP/profile; +liquidity/structure; +EMA100/regime; +AMD; +IFVG; +MFE overlay. Promote only additions that improve robustness.

- [ ] **Step 8: Out-of-sample / DEMO gate**

Run unseen-period validation, then DEMO forward testing with spread/slippage drift telemetry. LIVE remains blocked.

## Self-Review

- Spec coverage: all 17 design sections map to Tasks 1–12; no uncovered architectural requirement remains.
- Step scan: implementation steps specify one checkable action each; no speculative feature work is included.
- Type consistency: contexts flow into `V10Decision`, then into execution and position management; telemetry consumes those same fields.
- Review Focus: repeated entries, directional asymmetry, optional-context failure, fail-closed risk and exit interaction are each owned by Tasks 3, 8, 5/7, 4 and 10 respectively.
- Proportion: plan defines interfaces and evidence gates without transcribing the EA implementation.
