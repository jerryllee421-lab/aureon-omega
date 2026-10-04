# AUREON Ω V10.5 Ultimate EA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and certify an evidence-driven XAUUSD MT5 V10.5 challenger that adds liquidity/AMD/FVG-IFVG/VWAP-profile/order-flow intelligence without regressing V10.4 safety, execution integrity, or historical/live comparability.

**Architecture:** Preserve V10.4 as an immutable control and build V10.5 as a new challenger. Keep the top-level EA responsible for orchestration/execution/reconciliation while moving new deterministic intelligence into focused `.mqh` modules with explicit data-quality/state structs. New modules start as shadow/telemetry where required, are integrated behind ablation flags, and are promoted only after native MetaEditor compile, real-tick parity/OOS/stress testing, and DEMO forward validation.

**Tech Stack:** MQL5 / MetaTrader 5 Strategy Tester, PowerShell Windows CI runner, Python 3 standard-library contract/report tests, GitHub Actions Windows runner, PXBT XAUUSD real-tick history for authoritative tester evidence.

**Spec:** `docs/superpowers/specs/2026-10-04-aureon-v10-5-ultimate-ea-design.md`

## Global Constraints

- V10.4 is the immediate control; the frozen V2.12 benchmark remains a historical control.
- Target is XAUUSD / Gold on MT5.
- Structural signals use completed bars unless explicitly part of real-time tick/order-flow logic.
- No fabricated market data; every volume/flow path carries an explicit source-quality tier.
- Quote/tick proxies must never be labelled centralized or traded volume.
- DOM is SHADOW-ONLY in the first V10.5 certification release and cannot trigger, veto, resize, or close trades.
- Initial DEMO risk is `0.05%`; configured certification cap is `0.10%`.
- One managed position only.
- Daily-loss halt is `3%`; equity-drawdown halt is `6%`.
- Minimum anti-churn spacing remains `6 seconds`.
- Runaway ceiling remains `200 trades/day`.
- No martingale, grid, loss-recovery lot multiplier, or forced trade quota.
- LIVE account execution remains hard blocked throughout V10.5 development/certification.
- Native MT5 `Every tick based on real ticks` verification is mandatory before promotion.
- V10.5 must beat/retain controls through controlled ablation; complexity alone is not a promotion criterion.
- No single month/session/direction may contribute more than 50% of total positive R for a general-purpose promotion candidate unless the setup family was pre-specified as niche before testing.

## Review Focus

1. **Broker provides no usable trade-side flags:** flow must degrade to `FLOW_QUOTE_INFERRED` or `UNAVAILABLE`, never fabricate native delta. Covered in Task 7 tests.
2. **DOM is unavailable or changes during runtime:** trading behavior must remain identical because DOM is shadow-only. Covered in Task 8 tests.
3. **A breakout holds outside an accumulation range:** AMD must classify acceptance/distribution rather than falsely calling manipulation. Covered in Task 4 tests.
4. **An FVG is invalidated, inverted, and retested repeatedly:** exactly one active IFVG lifecycle may exist per original FVG and no duplicate re-entry loop is allowed. Covered in Task 5 tests.
5. **Restart occurs with an unresolved/closed broker position:** V10.4 exact-ID reconciliation and duplicate-close protection must remain fail-closed and idempotent. Covered in Task 10 regression tests.

---

## File Structure

### New production files

- `mt5/AUREON_OMEGA_V10_5_ULTIMATE_CANDIDATE.mq5` — V10.5 orchestration, existing execution/risk/reconciliation, module wiring, ablation switches.
- `mt5/include/AUREON/V10_5/MarketTruth.mqh` — tick/bar/broker-spec observations, source-quality classification, tick ring buffers.
- `mt5/include/AUREON/V10_5/LiquidityMap.mqh` — typed liquidity levels, equal-high/low clusters, sweep/reclaim classification.
- `mt5/include/AUREON/V10_5/AMD.mqh` — accumulation/manipulation/distribution state machine.
- `mt5/include/AUREON/V10_5/Imbalance.mqh` — FVG lifecycle plus IFVG inversion/retest lifecycle.
- `mt5/include/AUREON/V10_5/VWAPProfile.mqh` — trade/quote/bar VWAP hierarchy and volume/tick-frequency profile.
- `mt5/include/AUREON/V10_5/OrderFlow.mqh` — source-aware delta/CVD, velocity, absorption/exhaustion/divergence.
- `mt5/include/AUREON/V10_5/DOMShadow.mqh` — optional `MarketBook*` shadow telemetry only.
- `mt5/include/AUREON/V10_5/DecisionFusion.mqh` — regime-aware setup-family evidence states and contradiction handling.

### New test/support files

- `tests/mt5/test_v10_5_source_contract.py` — source-level safety/architecture invariants.
- `tests/mt5/test_v10_5_algorithms.py` — deterministic reference tests for sweep/AMD/FVG-IFVG/flow/profile math.
- `tests/mt5/fixtures/v10_5_synthetic_cases.json` — fixed synthetic scenarios shared by Python tests and MT5 self-test harness.
- `mt5/tests/AUREON_V10_5_SELFTEST.mq5` — MQL5 deterministic self-test harness over synthetic cases/pure module functions.
- `tools/mt5/v10_5_report_gate.py` — parses MT5 HTML/report evidence and enforces promotion metrics/concentration gates.
- `tests/mt5/test_v10_5_report_gate.py` — parser/gate tests with small fixtures.

### Existing files modified only where necessary

- `.github/scripts/run-mt5-backtest.ps1` — compile V10.5/self-test and select the candidate for dedicated tester runs without exposing credentials.
- `.github/workflows/mt5-v10-pxbt-backtest.yml` — only if the existing runner cannot select V10.5 without changing workflow inputs; never embed credentials.
- `docs/GOLD_VALIDATION_MASTER.md` — add V10.5 as a challenger only after compile/test evidence exists; do not mark promoted prematurely.

---

### Task 1: Freeze V10.4 control and create V10.5 skeleton

**Files:**
- Create: `mt5/AUREON_OMEGA_V10_4_RELIABILITY_CANDIDATE.mq5`
- Create: `mt5/AUREON_OMEGA_V10_5_ULTIMATE_CANDIDATE.mq5`
- Create: `tests/mt5/test_v10_5_source_contract.py`

**Interfaces:**
- Consumes: current V10.4 artifact SHA-256 `34915aa5349ca81f05ab46645835106ee3ee40c81a7a348699f6b5d9109b150b`.
- Produces: V10.5 main EA with version `10.50`, unique magic/research IDs, unchanged V10.4 execution/risk/reconciliation behavior, and include hooks for later modules.

- [ ] **Step 1: Write failing source-contract tests**

```python
def test_v10_4_control_hash_is_frozen(): ...
def test_v10_5_has_unique_version_magic_and_research_id(): ...
def test_v10_5_live_execution_is_hard_blocked(): ...
def test_v10_5_retains_risk_limits(): ...
```

Assertions must pin `0.05%` default risk, `0.10%` max risk, `3%` daily halt, `6%` DD halt, `6s` anti-churn, `200/day`, one-position behavior, and LIVE hard block.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.mt5.test_v10_5_source_contract -v`

Expected: FAIL because V10.4/V10.5 repository files and V10.5 identifiers do not yet exist.

- [ ] **Step 3: Add exact V10.4 artifact and create V10.5 skeleton**

Copy V10.4 byte-for-byte into the repository; fork V10.5 from it without changing strategy behavior yet. Add include directives only after the corresponding include files exist in later tasks.

- [ ] **Step 4: Run GREEN source-contract tests**

Run: `python -m unittest tests.mt5.test_v10_5_source_contract -v`

Expected: PASS.

- [ ] **Step 5: Native MetaEditor compile both controls**

Use existing Windows runner compile path. Expected: `0 errors, 0 warnings` for V10.4 and V10.5 skeleton.

- [ ] **Step 6: Commit**

```bash
git add mt5/AUREON_OMEGA_V10_4_RELIABILITY_CANDIDATE.mq5 mt5/AUREON_OMEGA_V10_5_ULTIMATE_CANDIDATE.mq5 tests/mt5/test_v10_5_source_contract.py
git commit -m "test: freeze v10.4 and scaffold v10.5 challenger"
```

### Task 2: Market Truth and data-quality layer

**Files:**
- Create: `mt5/include/AUREON/V10_5/MarketTruth.mqh`
- Modify: `mt5/AUREON_OMEGA_V10_5_ULTIMATE_CANDIDATE.mq5`
- Modify: `tests/mt5/test_v10_5_source_contract.py`
- Create/Modify: `tests/mt5/test_v10_5_algorithms.py`

**Interfaces:**
- Produces:
  - `enum ENUM_FLOW_SOURCE_QUALITY { FLOW_NONE, FLOW_QUOTE_INFERRED, FLOW_TRADE_INFERRED, FLOW_TRADE_NATIVE, FLOW_DOM }`
  - `struct MarketTruthState`
  - `bool BuildMarketTruth(const string symbol,const datetime now,MarketTruthState &out)`
  - `bool PushObservedTick(const MqlTick &tick,MarketTruthState &state)`
- Later tasks consume `MarketTruthState` only; they do not fetch undocumented raw terminal fields independently.

- [ ] **Step 1: Write failing tests** for source-quality enum, freshness, invalid bid/ask rejection, zero/missing volume handling, and no silent `FLOW_TRADE_NATIVE` without native evidence.
- [ ] **Step 2: Run RED** with `python -m unittest tests.mt5.test_v10_5_algorithms -v`; expected source/interface failures.
- [ ] **Step 3: Implement minimal MarketTruth structures/functions** including bounded tick ring buffers for 5s/15s/30s/60s calculations and broker-spec snapshot fields.
- [ ] **Step 4: Run GREEN Python tests** and source-contract tests.
- [ ] **Step 5: Add equivalent synthetic assertions to `AUREON_V10_5_SELFTEST.mq5`** for invalid spread/tick/source-quality cases.
- [ ] **Step 6: Native compile** main EA + self-test; expected `0 errors, 0 warnings`.
- [ ] **Step 7: Commit** with `feat: add v10.5 market truth layer`.

### Task 3: Typed liquidity map and sweep classifier

**Files:**
- Create: `mt5/include/AUREON/V10_5/LiquidityMap.mqh`
- Modify: V10.5 main EA
- Modify: algorithm tests + synthetic fixture

**Interfaces:**
- Produces:
  - `enum ENUM_LIQUIDITY_LEVEL_TYPE` covering previous-day, Asia, London/NY developing, swing, equal-high/low, local pool, FVG/IFVG boundary, and profile-location references.
  - `enum ENUM_SWEEP_CLASS { SWEEP_NONE, TOUCH, SHALLOW_SWEEP, VALID_SWEEP, DEEP_SWEEP, BREAK_ACCEPTANCE }`
  - `struct LiquidityLevel`, `struct SweepEvidence`, `struct LiquidityMapState`
  - `ENUM_SWEEP_CLASS ClassifySweep(...)`
  - `bool BuildLiquidityMap(...)`

- [ ] **Step 1: Write failing tests** for touch vs valid sweep vs deep sweep vs acceptance; bullish/bearish symmetry; equal-high/low clusters requiring at least two pivots inside ATR tolerance.
- [ ] **Step 2: Run RED**; expected missing classifier/interfaces.
- [ ] **Step 3: Implement classifier and map** using completed bars only.
- [ ] **Step 4: Run GREEN**; assert VWAP/POC levels are tagged location references, not automatically stop-liquidity.
- [ ] **Step 5: Native compile/self-test**.
- [ ] **Step 6: Commit** `feat: add typed liquidity sweep engine`.

### Task 4: AMD / Power-of-Three state machine

**Files:**
- Create: `mt5/include/AUREON/V10_5/AMD.mqh`
- Modify: V10.5 main EA
- Modify: tests + fixture

**Interfaces:**
- Produces:
  - `enum ENUM_AMD_PHASE { AMD_NONE, AMD_ACCUMULATION, AMD_MANIPULATION, AMD_DISTRIBUTION, AMD_BREAKOUT_ACCEPTED, AMD_EXPIRED }`
  - `struct AMDState`
  - `bool UpdateAMDState(const LiquidityMapState &liq,const MarketTruthState &truth,...,AMDState &state)`

- [ ] **Step 1: Write failing tests** for compressed range detection, bullish/bearish manipulation, accepted breakout not being misclassified as manipulation, expiry, and distribution requiring MSS/displacement evidence.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement minimal deterministic state machine** with explicit timeframe/min-age/max-age/width-ATR parameters frozen for the first parity run.
- [ ] **Step 4: Run GREEN** including Review Focus breakout-acceptance case.
- [ ] **Step 5: Compile/self-test**.
- [ ] **Step 6: Commit** `feat: add amd state machine`.

### Task 5: FVG lifecycle and IFVG inversion engine

**Files:**
- Create: `mt5/include/AUREON/V10_5/Imbalance.mqh`
- Modify: V10.5 main EA
- Modify: tests + fixture

**Interfaces:**
- Produces:
  - `enum ENUM_IMBALANCE_STATE { FVG_FRESH, FVG_PARTIAL, FVG_MITIGATED, FVG_INVALIDATED, FVG_INVERTED, FVG_EXPIRED }`
  - `struct FVGZone`, `struct IFVGState`
  - `bool DetectFVG(...)`
  - `void UpdateFVGZone(...)`
  - `bool PromoteToIFVG(...)`
  - `bool EvaluateIFVGRetest(...)`

- [ ] **Step 1: Write failing tests** preserving current 3-candle/displacement/ATR FVG definition, then add fill %, invalidation close-through, one-time inversion, retest/rejection, expiry, max-attempt behavior.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement FVG metadata/lifecycle without changing control FVG detection output for parity fixtures**.
- [ ] **Step 4: Implement IFVG inversion/retest minimally**; one original zone may own at most one active inversion state.
- [ ] **Step 5: Run GREEN**, including duplicate retest/re-entry-loop regression.
- [ ] **Step 6: Compile/self-test**.
- [ ] **Step 7: Commit** `feat: add fvg lifecycle and ifvg engine`.

### Task 6: Tick/trade VWAP and volume-at-price hierarchy

**Files:**
- Create: `mt5/include/AUREON/V10_5/VWAPProfile.mqh`
- Modify: V10.5 main EA
- Modify: tests + fixture

**Interfaces:**
- Produces:
  - `enum ENUM_PROFILE_SOURCE { PROFILE_NONE, PROFILE_BAR_PROXY, PROFILE_TICK_FREQUENCY, PROFILE_TRADE_VOLUME }`
  - `struct VWAPState`, `struct VolumeProfileState`
  - `bool BuildVWAPState(const MarketTruthState &truth,...,VWAPState &out)`
  - `bool BuildVolumeProfile(const MarketTruthState &truth,...,VolumeProfileState &out)`
- Outputs include VWAP/sigma/slope/source quality plus POC/VAH/VAL/HVN/LVN/developing POC/value-width/migration.

- [ ] **Step 1: Write failing tests** for weighted VWAP math, quote-frequency fallback, bar fallback, POC/VA 70% construction, source labels, and no false trade-volume claim.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement VWAP hierarchy**: native trade-volume first, quote/tick-frequency second, current M1 bar-derived fallback third.
- [ ] **Step 4: Implement profile hierarchy** with deterministic price bins; retain old equal-bar-distribution algorithm only as explicit `PROFILE_BAR_PROXY` control.
- [ ] **Step 5: Run GREEN** and compile/self-test.
- [ ] **Step 6: Commit** `feat: add source-aware vwap and volume profile`.

### Task 7: Source-aware order-flow engine

**Files:**
- Create: `mt5/include/AUREON/V10_5/OrderFlow.mqh`
- Modify: V10.5 main EA
- Modify: tests + fixture

**Interfaces:**
- Produces:
  - `struct FlowWindow { double delta; double normalized_delta; double imbalance; double tick_velocity; double velocity_accel; double directional_efficiency; ... }`
  - `struct OrderFlowState` with 5s/15s/30s/60s windows and session CVD.
  - `int InferAggressorSide(const MqlTick &prev,const MqlTick &cur,int carry_side,int carry_count)`
  - `bool BuildOrderFlowState(const MarketTruthState &truth,OrderFlowState &out)`
  - absorption/exhaustion/divergence evidence functions.

- [ ] **Step 1: Write failing tests** for native side flags, trade-vs-bid/ask inference, uptick/downtick, midpoint fallback, unchanged carry cap, CVD, velocity, absorption, exhaustion, divergence.
- [ ] **Step 2: Add explicit test:** no native trade-side flags => must not return `FLOW_TRADE_NATIVE`.
- [ ] **Step 3: Run RED**.
- [ ] **Step 4: Implement deterministic inference hierarchy exactly as spec**.
- [ ] **Step 5: Run GREEN** with source-tier-specific assertions.
- [ ] **Step 6: Compile/self-test**.
- [ ] **Step 7: Commit** `feat: add broker-aware order flow engine`.

### Task 8: DOM shadow telemetry

**Files:**
- Create: `mt5/include/AUREON/V10_5/DOMShadow.mqh`
- Modify: V10.5 main EA
- Modify: source-contract tests

**Interfaces:**
- Produces `struct DOMShadowState` and `bool UpdateDOMShadow(const string symbol,DOMShadowState &out)` using `MarketBookAdd`, `MarketBookGet`, and `MarketBookRelease` where supported.
- Must not be consumed by trade-trigger/veto/sizing/exit code in V10.5.

- [ ] **Step 1: Write failing source-contract tests** proving DOM functions exist but no production decision or sizing function references `DOMShadowState`.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement DOM subscription/metrics**: top-N bid/ask quantity, distance-weighted imbalance, microprice, replenishment/persistence approximations.
- [ ] **Step 4: Add runtime-unavailable path** returning `DOM_UNAVAILABLE` without changing trade decision.
- [ ] **Step 5: Run GREEN and native compile**.
- [ ] **Step 6: Commit** `feat: add shadow-only dom telemetry`.

### Task 9: Regime-aware decision fusion and canonical state machine

**Files:**
- Create: `mt5/include/AUREON/V10_5/DecisionFusion.mqh`
- Modify: V10.5 main EA
- Modify: tests + fixture

**Interfaces:**
- Produces:
  - `enum ENUM_EVIDENCE_STATE { EVIDENCE_FAIL, EVIDENCE_NEUTRAL, EVIDENCE_PASS, EVIDENCE_UNAVAILABLE }`
  - setup family enum: liquidity reversal, trend continuation, breakout/expansion.
  - canonical lifecycle: `SCANNING -> LIQUIDITY_IDENTIFIED -> SWEPT -> RECLAIMED -> MSS_CONFIRMED -> DISPLACED -> FVG_OR_IFVG_READY -> RETESTING -> FLOW_CONFIRMED -> MICRO_ARMED -> TRIGGERED`, plus terminal states from spec.
  - `struct DecisionEvidence`, `struct V105Decision`.
  - `V105Decision BuildV105Decision(...)`.

- [ ] **Step 1: Write failing tests** for each setup family using synthetic evidence objects.
- [ ] **Step 2: Verify:** liquidity reversal requires valid sweep+reclaim; trend continuation does not require AMD manipulation; accepted breakout does not pass reversal path.
- [ ] **Step 3: Run RED**.
- [ ] **Step 4: Implement evidence fusion** with contradictions explicitly recorded; unavailable optional data reduces evidence but does not fabricate confirmation.
- [ ] **Step 5: Wire existing 5s micro trigger as final timing layer**, not as a substitute for structure/flow.
- [ ] **Step 6: Run GREEN, compile/self-test**.
- [ ] **Step 7: Commit** `feat: add regime-aware v10.5 decision fusion`.

### Task 10: Execution, risk, reconciliation and telemetry regression gate

**Files:**
- Modify: V10.5 main EA
- Modify: source-contract tests
- Modify: self-test harness

**Interfaces:**
- Consumes `V105Decision`; emits immutable TradeIntent/evidence into existing execution path.
- Must retain V10.4 exact-ID persistence, duplicate-close protection, restart reconciliation, daily/DD governor, one-position rule, stop/margin/filling/spec validation, and LIVE hard block.

- [ ] **Step 1: Write failing/regression tests** asserting V10.4 safety constants and functions remain present and that `TRIGGERED` alone cannot bypass execution/risk gates.
- [ ] **Step 2: Add restart test fixtures** for unresolved position, already-accounted close, duplicate transaction, and broker/local mismatch.
- [ ] **Step 3: Run RED where new TradeIntent integration is absent; existing safety assertions must already PASS**.
- [ ] **Step 4: Wire V10.5 decision into existing fail-closed execution path** without changing risk limits.
- [ ] **Step 5: Expand execution telemetry** with setup family, liquidity/AMD/FVG-IFVG/VWAP/profile/flow source fields and contradiction list.
- [ ] **Step 6: Run all tests + native compile/self-test**; expected zero regressions.
- [ ] **Step 7: Commit** `feat: integrate v10.5 decision with fail-closed execution`.

### Task 11: Native compile/parity runner and report gate

**Files:**
- Modify: `.github/scripts/run-mt5-backtest.ps1`
- Create: `tools/mt5/v10_5_report_gate.py`
- Create: `tests/mt5/test_v10_5_report_gate.py`
- Add small sanitized HTML/CSV fixtures under `tests/mt5/fixtures/`.

**Interfaces:**
- Report gate: `evaluate_report(report_path: str, telemetry_path: str | None) -> GateResult`.
- `GateResult` includes metrics, concentration diagnostics, data-quality tier, and explicit PASS/FAIL reasons.

- [ ] **Step 1: Write failing parser/gate tests** for PF, WR, drawdown, trade count, dates/model/history quality, direction/session/month contribution and malformed/missing report behavior.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement report parser/gates**; malformed or incomplete evidence fails closed.
- [ ] **Step 4: Update Windows runner** to compile V10.5 + self-test before any broker credential gate and to select V10.5 explicitly for its dedicated tester job. Do not add plaintext credentials or sensitive endpoints.
- [ ] **Step 5: Run GREEN unit tests**.
- [ ] **Step 6: Trigger native Windows compile**; require `0 errors, 0 warnings` for V10.4/V10.5/self-test.
- [ ] **Step 7: Commit** `test: add native v10.5 compile and report gates`.

### Task 12: Controlled backtest, ablation, OOS and stress campaign

**Files:**
- Create: `docs/research/V10_5_CERTIFICATION_MATRIX.md`
- Generated evidence goes under CI artifacts/reports, not committed secrets.

**Interfaces:**
- Consumes V10.4 and V10.5 EX5/report artifacts.
- Produces a decision table with same-period parity, ablations, untouched periods, walk-forward, cost stress, parameter stability and concentration diagnostics.

- [ ] **Step 1: Run V10.4 and V10.5 same-period parity** with identical broker/symbol/model/deposit/leverage/date assumptions.
- [ ] **Step 2: Run ablations separately:** liquidity-map only; AMD; IFVG; tick/profile; order flow; full fusion. DOM remains shadow-only and cannot alter fills.
- [ ] **Step 3: Run untouched OOS chronological blocks** without retuning on those blocks.
- [ ] **Step 4: Run walk-forward blocks** and record parameter stability.
- [ ] **Step 5: Stress spread/slippage/latency/symbol specs**, including at least +50% execution-cost stress versus baseline assumptions.
- [ ] **Step 6: Analyze BUY/SELL, London/NY/other session, month, setup-family and regime concentration**; general candidate fails if any unplanned bucket >50% of positive R.
- [ ] **Step 7: Run Monte Carlo realized-R sequence analysis** and document tail DD.
- [ ] **Step 8: Write certification matrix** with verified metrics only; no invented results.
- [ ] **Step 9: Commit research matrix template/evidence summary** `test: document v10.5 certification evidence`.

### Task 13: DEMO forward canary and promotion decision

**Files:**
- Modify: `docs/GOLD_VALIDATION_MASTER.md`
- Create: `docs/research/V10_5_FORWARD_CANARY.md`
- Generated telemetry remains runtime evidence/artifacts.

**Interfaces:**
- Consumes the historically certified decisive path; DOM metrics remain observational.
- Produces 20/50/100-trade reconciliation checkpoints and final promote/reject verdict.

- [ ] **Step 1: Start PXBT DEMO only after Tasks 1-12 pass**, with LIVE hard block verified at startup.
- [ ] **Step 2: Checkpoint after 20 genuine trades:** zero orphan positions/orders, zero unresolved reconciliation mismatches, execution/slippage telemetry complete.
- [ ] **Step 3: Checkpoint after 50 trades:** forward PF/WR/expectancy/drift, source-quality mix, setup-family concentration and broker execution integrity.
- [ ] **Step 4: Checkpoint after 100 trades:** repeat full forward analysis; compare to historically backtestable path without crediting DOM shadow data as causal.
- [ ] **Step 5: Fail promotion immediately** on any LIVE execution, reconciliation defect, duplicate intent/close, missing SL, persistent stale data, or governor violation.
- [ ] **Step 6: Update `GOLD_VALIDATION_MASTER.md`** only with verified status: `CHALLENGER_REJECTED`, `CHALLENGER_CONTINUE_RESEARCH`, or `PRELIVE_CERTIFIED`. Do not call it live-ready solely from backtest results.
- [ ] **Step 7: Commit** `docs: record v10.5 forward certification verdict`.

---

## Full Verification Command Set

Run before any completion claim:

```bash
python -m unittest discover -s tests/mt5 -p 'test_v10_5_*.py' -v
```

Then require the Windows MT5 runner to report:

- V10.4 native compile: `0 errors, 0 warnings`
- V10.5 native compile: `0 errors, 0 warnings`
- V10.5 self-test compile/run: PASS
- Strategy Tester model: `Every tick based on real ticks`
- requested period/config recorded in manifest
- report gate: explicit PASS/FAIL with reasons

No result may be called verified if only the GitHub workflow status is green but the MetaEditor/tester/report evidence is absent.
