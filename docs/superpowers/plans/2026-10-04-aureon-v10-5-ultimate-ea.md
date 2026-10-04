# AUREON Ω V10.5 Ultimate EA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and certify an evidence-driven XAUUSD MT5 V10.5 challenger that adds liquidity/AMD/FVG-IFVG/VWAP-profile/order-flow intelligence without regressing V10.4 safety, execution integrity, or historical/live comparability.

**Architecture:** Preserve V10.4 byte-for-byte as the immediate control. Build V10.5 as a new challenger whose top-level EA keeps execution/risk/reconciliation while new deterministic intelligence lives in focused `.mqh` modules. Every feature is test-first, ablatable, source-quality-labelled, and promoted only after native MetaEditor compile, real-tick MT5 evidence, OOS/stress testing, and DEMO forward validation.

**Tech Stack:** MQL5 / MetaTrader 5 Strategy Tester, PowerShell Windows CI runner, Python 3 standard-library tests/report parser, GitHub Actions Windows runner, PXBT XAUUSD real-tick history.

**Spec:** `docs/superpowers/specs/2026-10-04-aureon-v10-5-ultimate-ea-design.md`

## Global Constraints

- V10.4 is the immediate control; frozen V2.12 remains a historical control.
- XAUUSD / Gold only for this certification lane.
- Structural features use completed bars; only tick/order-flow/micro layers may use current observations.
- Never fabricate unavailable market data or call a proxy native/centralized volume.
- DOM is SHADOW-ONLY in V10.5 and cannot trigger, veto, resize, or close a trade.
- Initial DEMO risk `0.05%`; certification cap `0.10%`.
- One managed position only.
- Daily-loss halt `3%`; equity-drawdown halt `6%`.
- Minimum anti-churn spacing `6 seconds`; runaway ceiling `200 trades/day`.
- No martingale, grid, loss-recovery sizing, or forced trade quota.
- LIVE execution remains hard blocked throughout V10.5 development/certification.
- Native MT5 `Every tick based on real ticks` evidence is mandatory before promotion.
- Directional risk multipliers remain an ablation hypothesis, not permanent truth.
- A general-purpose candidate fails concentration review if an unplanned single month/session/direction contributes >50% of total positive R.

## Review Focus

1. **No usable trade-side flags:** degrade to `FLOW_QUOTE_INFERRED`/`UNAVAILABLE`; never fabricate `FLOW_TRADE_NATIVE`. Task 7.
2. **DOM unavailable or unstable:** decisive trading behavior must remain unchanged because DOM is shadow-only. Task 8.
3. **Breakout accepts outside accumulation:** classify acceptance/distribution, not manipulation. Task 4.
4. **FVG invalidates/inverts/retests repeatedly:** one active IFVG lifecycle per source FVG; no duplicate re-entry loop. Task 5.
5. **Restart with unresolved/closed position:** exact-ID reconciliation remains fail-closed and idempotent. Task 10.

---

## File Structure

**Production**
- `mt5/AUREON_OMEGA_V10_4_RELIABILITY_CANDIDATE.mq5` — immutable control.
- `mt5/AUREON_OMEGA_V10_5_ULTIMATE_CANDIDATE.mq5` — orchestration/execution/risk/reconciliation/module wiring.
- `mt5/include/AUREON/V10_5/MarketTruth.mqh` — data quality, tick observations, broker spec.
- `mt5/include/AUREON/V10_5/LiquidityMap.mqh` — typed levels, equal highs/lows, sweep/reclaim.
- `mt5/include/AUREON/V10_5/AMD.mqh` — accumulation/manipulation/distribution state machine.
- `mt5/include/AUREON/V10_5/Imbalance.mqh` — FVG lifecycle + IFVG inversion.
- `mt5/include/AUREON/V10_5/VWAPProfile.mqh` — source-aware VWAP and profile.
- `mt5/include/AUREON/V10_5/OrderFlow.mqh` — delta/CVD/velocity/absorption/exhaustion/divergence.
- `mt5/include/AUREON/V10_5/DOMShadow.mqh` — forward-only shadow DOM telemetry.
- `mt5/include/AUREON/V10_5/DecisionFusion.mqh` — setup families/evidence/state machine.

**Tests/support**
- `tests/mt5/test_v10_5_source_contract.py`
- `tests/mt5/test_v10_5_algorithms.py`
- `tests/mt5/test_v10_5_report_gate.py`
- `tests/mt5/fixtures/v10_5_synthetic_cases.json`
- `mt5/tests/AUREON_V10_5_SELFTEST.mq5`
- `tools/mt5/v10_5_report_gate.py`

**Existing infrastructure**
- `.github/scripts/run-mt5-backtest.ps1`
- `.github/workflows/mt5-v10-pxbt-backtest.yml` only if candidate selection cannot be done safely in the existing runner.
- `docs/GOLD_VALIDATION_MASTER.md` only after evidence exists.

---

### Task 1: Freeze V10.4 and scaffold V10.5

**Files:** create V10.4/V10.5 main files and `tests/mt5/test_v10_5_source_contract.py`.

**Interfaces:** V10.4 artifact SHA-256 must equal `34915aa5349ca81f05ab46645835106ee3ee40c81a7a348699f6b5d9109b150b`; V10.5 starts at version `10.50` with unique magic/research IDs.

- [ ] Write failing tests: `test_v10_4_control_hash_is_frozen`, `test_v10_5_has_unique_identity`, `test_live_execution_is_hard_blocked`, `test_v10_5_retains_certification_risk_limits`.
- [ ] Run RED: `python -m unittest discover -s tests/mt5 -p 'test_v10_5_source_contract.py' -v`; expect V10.4/V10.5 file/identity failures.
- [ ] Copy V10.4 byte-for-byte; fork V10.5 without strategy behavior changes.
- [ ] Run GREEN with the same command.
- [ ] Native compile V10.4 + V10.5 skeleton; require `0 errors, 0 warnings`.
- [ ] Commit: `test: freeze v10.4 and scaffold v10.5 challenger`.

### Task 2: Market Truth and source-quality layer

**Files:** create `MarketTruth.mqh`; modify V10.5 main/tests/self-test.

**Interfaces:**
- `enum ENUM_FLOW_SOURCE_QUALITY { FLOW_NONE, FLOW_QUOTE_INFERRED, FLOW_TRADE_INFERRED, FLOW_TRADE_NATIVE, FLOW_DOM }`
- `struct MarketTruthState`
- `bool PushObservedTick(const MqlTick &tick,MarketTruthState &state)`
- `bool BuildMarketTruth(const string symbol,const datetime now,MarketTruthState &out)`

- [ ] Write failing tests for invalid bid/ask, stale tick, zero/missing volume, bounded 5s/15s/30s/60s observations, and no native-flow label without native evidence.
- [ ] Run RED: `python -m unittest discover -s tests/mt5 -p 'test_v10_5_algorithms.py' -v`.
- [ ] Implement only the state/source-quality/broker-spec/tick-buffer behavior required by tests.
- [ ] Add equivalent synthetic self-test assertions.
- [ ] Run GREEN + native compile/self-test.
- [ ] Commit: `feat: add v10.5 market truth layer`.

### Task 3: Liquidity map and sweep classifier

**Files:** create `LiquidityMap.mqh`; modify main/tests/fixture.

**Interfaces:**
- `enum ENUM_LIQUIDITY_LEVEL_TYPE`
- `enum ENUM_SWEEP_CLASS { SWEEP_NONE, TOUCH, SHALLOW_SWEEP, VALID_SWEEP, DEEP_SWEEP, BREAK_ACCEPTANCE }`
- `struct LiquidityLevel`, `SweepEvidence`, `LiquidityMapState`
- `ENUM_SWEEP_CLASS ClassifySweep(const int direction,const double level,const double bar_high,const double bar_low,const double bar_close,const double atr,SweepEvidence &out)`
- `bool DetectEqualLiquidityCluster(const double &pivot_prices[],const int pivot_count,const double atr,const double tolerance_atr,LiquidityLevel &out)`

- [ ] Write failing tests for bullish/bearish touch, valid sweep+reclaim, deep sweep, accepted break, and >=2-pivot equal-high/low clusters.
- [ ] Run RED.
- [ ] Implement completed-bar classifier/map; previous-day/Asia/London/NY/swing/equal/local/FVG/IFVG levels are typed separately.
- [ ] Test that VWAP/POC/VAH/VAL are location references, not automatically stop-liquidity.
- [ ] Run GREEN + compile/self-test.
- [ ] Commit: `feat: add typed liquidity sweep engine`.

### Task 4: AMD / Power-of-Three state machine

**Files:** create `AMD.mqh`; modify main/tests/fixture.

**Interfaces:**
- `enum ENUM_AMD_PHASE { AMD_NONE, AMD_ACCUMULATION, AMD_MANIPULATION, AMD_DISTRIBUTION, AMD_BREAKOUT_ACCEPTED, AMD_EXPIRED }`
- `struct AMDState`
- `ENUM_AMD_PHASE AdvanceAMD(AMDState &state,const datetime now,const double close,const double range_high,const double range_low,const double atr,const SweepEvidence &sweep,const bool mss,const bool displacement)`

- [ ] Write failing tests for accumulation compression/age, bullish/bearish manipulation, expiry, distribution confirmation, and accepted breakout not being manipulation.
- [ ] Run RED.
- [ ] Implement deterministic state transitions with first-parity parameters frozen before the run.
- [ ] Run GREEN including Review Focus #3.
- [ ] Native compile/self-test.
- [ ] Commit: `feat: add amd state machine`.

### Task 5: FVG lifecycle and IFVG inversion

**Files:** create `Imbalance.mqh`; modify main/tests/fixture.

**Interfaces:**
- `enum ENUM_IMBALANCE_STATE { FVG_FRESH, FVG_PARTIAL, FVG_MITIGATED, FVG_INVALIDATED, FVG_INVERTED, FVG_EXPIRED }`
- `struct FVGZone`, `IFVGState`
- `bool DetectFVG(const MqlRates &oldest,const MqlRates &middle,const MqlRates &newest,const int direction,const double atr,FVGZone &out)`
- `void UpdateFVGZone(const double high,const double low,const double close,const datetime now,FVGZone &zone)`
- `bool PromoteToIFVG(const FVGZone &zone,const double close,const double atr,const datetime now,IFVGState &out)`
- `bool EvaluateIFVGRetest(const double high,const double low,const double close,const datetime now,IFVGState &state)`

- [ ] Write failing tests preserving V10.4 3-candle/displacement/ATR behavior plus fill %, invalidation, one-time inversion, retest, expiry, max attempts.
- [ ] Run RED.
- [ ] Implement FVG metadata/lifecycle without changing control parity fixtures.
- [ ] Implement one-active-inversion-per-source FVG and duplicate-retest protection.
- [ ] Run GREEN including Review Focus #4; compile/self-test.
- [ ] Commit: `feat: add fvg lifecycle and ifvg engine`.

### Task 6: Tick/trade VWAP and volume-at-price

**Files:** create `VWAPProfile.mqh`; modify main/tests/fixture.

**Interfaces:**
- `enum ENUM_PROFILE_SOURCE { PROFILE_NONE, PROFILE_BAR_PROXY, PROFILE_TICK_FREQUENCY, PROFILE_TRADE_VOLUME }`
- `struct VWAPState`, `VolumeProfileState`
- `bool ComputeVWAP(const double &prices[],const double &weights[],const int count,double &vwap,double &sigma)`
- `bool ComputeVolumeProfile(const double &prices[],const double &weights[],const int count,const int bins,const double value_area_fraction,VolumeProfileState &out)`

- [ ] Write failing math/source tests: weighted VWAP, sigma, quote-frequency fallback, 70% value area, POC/HVN/LVN, developing POC migration, and no false trade-volume label.
- [ ] Run RED.
- [ ] Implement hierarchy: native trade-volume -> quote/tick-frequency -> existing M1 bar-derived proxy.
- [ ] Preserve daily/London/NY/anchored contexts and explicit source quality.
- [ ] Run GREEN + compile/self-test.
- [ ] Commit: `feat: add source-aware vwap and volume profile`.

### Task 7: Source-aware order flow

**Files:** create `OrderFlow.mqh`; modify main/tests/fixture.

**Interfaces:**
- `struct FlowWindow`, `OrderFlowState`
- `int InferAggressorSide(const MqlTick &prev,const MqlTick &cur,const int carry_side,const int carry_count,const int max_carry)`
- `bool BuildOrderFlowState(const MarketTruthState &truth,OrderFlowState &out)`
- `bool DetectAbsorption(const int direction,const FlowWindow &flow,const double price_progress_atr)`
- `bool DetectExhaustion(const int direction,const FlowWindow &fast,const FlowWindow &slow,const bool new_extreme)`
- `bool DetectDeltaDivergence(const int direction,const double price_extreme_now,const double price_extreme_prev,const double delta_now,const double delta_prev)`

- [ ] Write failing tests for native side flags, last-vs-bid/ask inference, uptick/downtick, midpoint fallback, capped unchanged carry, CVD, velocity/acceleration, absorption/exhaustion/divergence.
- [ ] Explicitly assert missing side flags can never yield `FLOW_TRADE_NATIVE`.
- [ ] Run RED.
- [ ] Implement deterministic source hierarchy and 5s/15s/30s/60s/session windows.
- [ ] Run GREEN including Review Focus #1; compile/self-test.
- [ ] Commit: `feat: add broker-aware order flow engine`.

### Task 8: DOM shadow telemetry

**Files:** create `DOMShadow.mqh`; modify main/source-contract tests.

**Interfaces:**
- `struct DOMShadowState`
- `bool UpdateDOMShadow(const string symbol,DOMShadowState &out)` using `MarketBookAdd`, `MarketBookGet`, `MarketBookRelease` only when supported.

- [ ] Write failing source-contract test proving DOM state is never referenced by trigger/veto/sizing/SL/TP/exit decisions.
- [ ] Run RED.
- [ ] Implement top-N bid/ask quantity, distance-weighted imbalance, microprice, replenishment/persistence telemetry and `DOM_UNAVAILABLE` fallback.
- [ ] Run GREEN including Review Focus #2; native compile.
- [ ] Commit: `feat: add shadow-only dom telemetry`.

### Task 9: Regime-aware decision fusion

**Files:** create `DecisionFusion.mqh`; modify main/tests/fixture.

**Interfaces:**
- `enum ENUM_EVIDENCE_STATE { EVIDENCE_FAIL, EVIDENCE_NEUTRAL, EVIDENCE_PASS, EVIDENCE_UNAVAILABLE }`
- `enum ENUM_SETUP_FAMILY { SETUP_LIQUIDITY_REVERSAL, SETUP_TREND_CONTINUATION, SETUP_BREAKOUT_EXPANSION }`
- canonical lifecycle from `SCANNING` through `TRIGGERED` plus terminal states in the spec.
- `struct DecisionEvidence`, `V105Decision`
- `V105Decision BuildV105Decision(const ENUM_SETUP_FAMILY family,const SweepEvidence &sweep,const AMDState &amd,const FVGZone &fvg,const IFVGState &ifvg,const VWAPState &vwap,const VolumeProfileState &profile,const OrderFlowState &flow,const bool mss,const bool displacement,const bool micro_trigger,const bool execution_available)`

- [ ] Write failing synthetic tests for all three setup families and contradictions.
- [ ] Assert reversal requires sweep+reclaim; continuation does not require AMD manipulation; accepted breakout cannot pass reversal path.
- [ ] Run RED.
- [ ] Implement evidence states/source quality/contradiction list; unavailable optional evidence cannot be invented as PASS.
- [ ] Keep existing 5s micro trigger as the final timing layer, not a replacement for structure/flow.
- [ ] Run GREEN + compile/self-test.
- [ ] Commit: `feat: add regime-aware v10.5 decision fusion`.

### Task 10: Stop/target geometry, TradeIntent, risk and reconciliation

**Files:** modify V10.5 main/source-contract/self-test.

**Interfaces:**
- `struct V105TradeIntent` containing immutable signal ID, setup family, direction, entry reference, SL, TP1/TP2/TP3, volume, risk %, source-quality/evidence snapshot, creation time.
- `bool ResolveV105Stop(const int direction,const double entry,const double atr,const SweepEvidence &sweep,const FVGZone &fvg,const IFVGState &ifvg,const double swing_level,double &sl_out)`
- `bool ResolveV105Targets(const int direction,const double entry,const double risk_distance,const LiquidityMapState &liq,const VWAPState &vwap,const VolumeProfileState &profile,double &tp1,double &tp2,double &tp3)`
- `bool BuildV105TradeIntent(const V105Decision &decision,const GoldContext &gold,const FeatureContext &control,V105TradeIntent &out)`

- [ ] Write failing tests for stop priority beyond sweep/manipulation/FVG-IFVG/swing with ATR buffer and broker-valid minimum distance.
- [ ] Write failing tests for ordered targets using liquidity/VWAP/profile/HVN-LVN candidates with minimum-R rules and fixed-R fallback.
- [ ] Add regression tests for one-position, `0.05/0.10%`, 3%/6% governors, 6s anti-churn, 200/day, missing-SL rejection, margin/filling/stops/freeze validation, LIVE hard block.
- [ ] Add restart fixtures for unresolved position, already-accounted close, duplicate transaction, broker/local mismatch.
- [ ] Run RED for new geometry/TradeIntent while existing V10.4 safety assertions remain green.
- [ ] Implement geometry + immutable intent and wire it into existing fail-closed execution path.
- [ ] Expand telemetry with setup/liquidity/AMD/FVG-IFVG/VWAP/profile/flow/contradictions and actual execution evidence.
- [ ] Run GREEN including Review Focus #5 + native compile/self-test.
- [ ] Commit: `feat: integrate v10.5 intent with fail-closed execution`.

### Task 11: Native runner and report gate

**Files:** modify `.github/scripts/run-mt5-backtest.ps1`; create report parser/tests/fixtures; modify workflow only if unavoidable.

**Interfaces:**
- Python `evaluate_report(report_path: str, telemetry_path: str | None) -> GateResult`.
- `GateResult` contains verified metrics, model/history/date checks, source-quality mix, concentration diagnostics and explicit PASS/FAIL reasons.

- [ ] Write failing report tests for PF, WR, DD, trades, dates/model/history quality, malformed/missing evidence, direction/session/month/setup concentration.
- [ ] Run RED: `python -m unittest discover -s tests/mt5 -p 'test_v10_5_report_gate.py' -v`.
- [ ] Implement fail-closed parser/gates.
- [ ] Update Windows runner to compile V10.4/V10.5/self-test before broker credential gate and select V10.5 explicitly for dedicated tester runs; never write plaintext credentials.
- [ ] Run GREEN.
- [ ] Trigger native compile; require `0 errors, 0 warnings` and self-test PASS.
- [ ] Commit: `test: add native v10.5 compile and report gates`.

### Task 12: Controlled backtest/ablation/OOS/stress campaign

**Files:** create `docs/research/V10_5_CERTIFICATION_MATRIX.md`; runtime reports remain artifacts.

- [ ] Run V10.4 vs V10.5 same-period parity with identical symbol/model/deposit/leverage/dates.
- [ ] Run ablations separately: liquidity map; AMD; IFVG; tick/profile; order flow; full fusion. DOM remains shadow-only.
- [ ] Run untouched chronological OOS blocks without retuning.
- [ ] Run walk-forward blocks and parameter-neighbour stability.
- [ ] Stress spread/slippage/latency/symbol specs including +50% execution-cost stress.
- [ ] Analyze BUY/SELL, session, month, regime and setup-family concentration; general candidate fails unplanned >50% positive-R concentration.
- [ ] Run Monte Carlo realized-R sequence analysis and document tail DD.
- [ ] Write certification matrix using verified values only; no fabricated results.
- [ ] Commit: `test: document v10.5 certification evidence`.

### Task 13: PXBT DEMO forward canary and verdict

**Files:** create `docs/research/V10_5_FORWARD_CANARY.md`; update `docs/GOLD_VALIDATION_MASTER.md` only with verified status.

- [ ] Start PXBT DEMO only after Tasks 1-12 pass and LIVE hard block is verified.
- [ ] At 20 genuine trades require zero orphan orders/positions, zero unresolved mismatches and complete execution/slippage evidence.
- [ ] At 50 trades evaluate forward PF/WR/expectancy/drift, source-quality mix, setup concentration and execution integrity.
- [ ] At 100 trades repeat full forward analysis against the historically backtestable decisive path; DOM shadow data gets no causal credit.
- [ ] Fail promotion immediately on LIVE execution, reconciliation defect, duplicate intent/close, missing SL, persistent stale data or governor violation.
- [ ] Record only `CHALLENGER_REJECTED`, `CHALLENGER_CONTINUE_RESEARCH`, or `PRELIVE_CERTIFIED`; backtests alone can never yield live-ready status.
- [ ] Commit: `docs: record v10.5 forward certification verdict`.

---

## Full Verification

Run before any completion claim:

```bash
python -m unittest discover -s tests/mt5 -p 'test_v10_5_*.py' -v
```

Then require the Windows MT5 evidence to show:
- V10.4 native compile `0 errors, 0 warnings`.
- V10.5 native compile `0 errors, 0 warnings`.
- V10.5 self-test compile/run PASS.
- Strategy Tester model `Every tick based on real ticks`.
- Requested period/config recorded in manifest.
- Report gate explicit PASS/FAIL with reasons.

A green GitHub workflow alone is not verification when MetaEditor/tester/report evidence is absent.
