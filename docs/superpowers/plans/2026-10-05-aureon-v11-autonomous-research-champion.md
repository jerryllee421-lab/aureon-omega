# AUREON Ω V11 — AUTONOMOUS RESEARCH CHAMPION Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one zero-configuration MQL5 EA that evaluates ten embedded Gold strategy lanes concurrently on the same XAUUSD M1 real-tick stream, isolates each lane’s shadow account state, produces per-lane telemetry and an automatic leaderboard, and preserves a measurable V2.17 control lane.

**Architecture:** The EA is a single self-contained `.mq5` file with shared market-state extraction and ten isolated lane states. All lanes use the same deterministic tick/bar stream and shared feature snapshot, but each lane owns independent shadow trades, balances, MFE/MAE, re-entry state, session attribution, exit family, and statistics. Only an optional designated tester lane may submit real Strategy Tester orders; Candidate 1 defaults to shadow-only research to prevent cross-lane interference.

**Tech Stack:** MQL5 / MetaTrader 5 Strategy Tester / `CTrade` only for optional tester sanity execution / CSV via native MQL5 file APIs / no external services.

**Spec:** `docs/superpowers/specs/2026-10-05-aureon-v11-autonomous-research-champion-design.md`

## Global Constraints

- Required source name: `AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`.
- Required banner: `AUREON Ω V11 ARC | build 20261005-01 | autonomous multi-lane research | zero-config`.
- Primary benchmark: XAUUSD, M1, Every tick based on real ticks, 2026-01-01 through 2026-10-02, $10,000 reference balance, 1:100 leverage, default inputs unchanged.
- All strategy/risk/session/telemetry defaults required for the benchmark must be embedded in source; no `.set` file dependency and no manual parameter tuning.
- Candidate 1 includes ten lanes: V2.17 control, controlled FVG, IFVG reversal, FVG+VWAP/Profile, FVG+EMA100, FVG+Liquidity/Structure, FVG+AMD, Full Hybrid, London, New York.
- Default shadow risk is 0.25% virtual fixed-fractional per trade; no martingale, no grid, no hidden lane-specific compounding advantage.
- Candidate 1 is research-only: Gold/XAU enforcement, LIVE execution blocked, no external AI/API dependency.
- One shared market snapshot may be reused across lanes, but lane trade/account/re-entry/statistics state must never be shared.
- Shadow fills must include spread and one common embedded slippage assumption; no zero-friction fills.
- Candidate 1 does not self-modify or promote its own parameters.

## Review Focus

1. **Lane contamination:** one lane opening/closing a shadow trade must not mutate another lane’s balance, position, FVG entry count, cooldown, or statistics. Task 3 adds explicit isolation tests.
2. **Same-tick look-ahead:** FVG/IFVG and session/context signals must use only closed-bar information where the lane rules require confirmation. Task 2 pins closed-bar indexing.
3. **Shadow fill realism:** long entries use ask-equivalent cost and short entries use bid-equivalent cost with the same slippage model across all lanes. Task 4 tests directionally correct friction.
4. **Leaderboard small-sample bias:** a lane with PF > 2 on fewer than 30 trades must be marked insufficient and cannot outrank a statistically usable positive-expectancy lane solely on PF. Task 9 tests the rank gate.
5. **Build identity drift:** Journal banner, magic/telemetry identifiers, source version constant, and exported CSV build id must match exactly. Task 1 and Task 10 verify identity.

---

### Task 1: V11 Shell, Embedded Configuration, and Build Identity

**Files:**
- Create: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_source_contract.py`

**Interfaces:**
- Produces: `V11_BUILD_ID`, `ENUM_RESEARCH_LANE`, `LaneConfig g_laneConfig[10]`, `IsGoldSymbol()`, `IsResearchEnvironmentAllowed()`, and one `OnInit()` that initializes all embedded defaults.
- Consumes: none.

- [ ] **Step 1: Write failing source-contract tests** asserting the exact source filename, build id `20261005-01`, required banner text, ten lane enum members, 0.25% default research risk, XAU enforcement, LIVE block, unique telemetry filenames, and absence of any dependency on `.set` files or external APIs.
- [ ] **Step 2: Run `python -m pytest tests/v11/test_v11_source_contract.py -v`** and verify failure because the V11 source does not yet exist.
- [ ] **Step 3: Implement the minimal V11 shell** with exact build constants, lane enum `LANE_A_V217_CONTROL` through `LANE_J_NEWYORK`, `LaneConfig`, zero-config defaults, banner print, XAU guard, tester/DEMO-only execution guard, and `OnInit()` initialization.
- [ ] **Step 4: Run the source-contract test** and verify PASS.
- [ ] **Step 5: Commit** with `feat(v11): add autonomous research shell and build identity`.

### Task 2: Shared Market Snapshot and FVG/IFVG Lifecycle Extraction

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_market_state_contract.py`

**Interfaces:**
- Consumes: `ENUM_RESEARCH_LANE`, embedded M1 timeframe constants from Task 1.
- Produces: `MarketSnapshot BuildMarketSnapshot()`, `FVGEvent DetectFVGClosedBars(const MarketSnapshot&)`, `UpdateFVGState(...)`, lifecycle enum values `FVG_FRESH`, `FVG_PARTIALLY_MITIGATED`, `FVG_HELD`, `FVG_INVALIDATED`, `IFVG_BULLISH`, `IFVG_BEARISH`, `FVG_EXPIRED`.

- [ ] **Step 1: Write failing tests** asserting closed-bar indexing for FVG formation, presence of all lifecycle states, explicit invalidation before IFVG reversal, and no use of the current forming bar as confirmation.
- [ ] **Step 2: Run the test** and verify failure on missing snapshot/lifecycle interfaces.
- [ ] **Step 3: Implement shared market extraction** for bid/ask/spread, M1 closed bars, ATR, EMA100 context, VWAP inputs, swing/liquidity inputs, session bucket, and FVG/IFVG lifecycle transitions.
- [ ] **Step 4: Run the market-state tests** and verify PASS.
- [ ] **Step 5: Commit** with `feat(v11): add shared market snapshot and fvg lifecycle`.

### Task 3: Isolated Lane State and Virtual Accounts

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_lane_isolation.py`

**Interfaces:**
- Consumes: `ENUM_RESEARCH_LANE`, `FVGEvent`, `MarketSnapshot`.
- Produces: `ShadowPosition`, `LaneStats`, `LaneState g_laneState[10]`, `ResetLaneState(int lane)`, `ResetAllLaneStates()`.

- [ ] **Step 1: Write failing isolation tests** verifying each lane has independent balance/equity, shadow position, entry counter, last outcome, cooldown, FVG id/state, MFE/MAE, and drawdown tracking.
- [ ] **Step 2: Run the isolation test** and verify failure because lane-state structures are absent.
- [ ] **Step 3: Implement lane-local state containers** initialized from a $10,000 virtual reference balance with 0.25% risk normalization and no cross-lane pointers/references.
- [ ] **Step 4: Run isolation tests** and verify PASS.
- [ ] **Step 5: Commit** with `feat(v11): isolate shadow account state per research lane`.

### Task 4: Deterministic Shadow Execution and Common Friction Model

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_shadow_execution.py`

**Interfaces:**
- Consumes: `LaneState`, `MarketSnapshot`, `TradeIntent`.
- Produces: `OpenShadowTrade(int lane,const TradeIntent&,const MarketSnapshot&)`, `UpdateShadowTrade(int lane,const MarketSnapshot&)`, `CloseShadowTrade(int lane,ENUM_EXIT_REASON,const MarketSnapshot&)`, `ComputeShadowFill(...)`.

- [ ] **Step 1: Write failing tests** for long/short fill-side correctness, embedded slippage, SL/TP hit ordering, MFE/MAE updates, fixed-fractional risk sizing in normalized R, and one-open-position-per-lane behavior.
- [ ] **Step 2: Run the tests** and verify failure on missing shadow execution functions.
- [ ] **Step 3: Implement deterministic shadow fills** using the common spread/slippage model, lane-local risk, SL/TP, MFE/MAE, realized R/P&L, balance/equity, peak equity, and drawdown proxy.
- [ ] **Step 4: Run shadow execution tests** and verify PASS.
- [ ] **Step 5: Commit** with `feat(v11): add deterministic shadow execution engine`.

### Task 5: Core Lane Signal Engines A–C

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_core_lanes.py`

**Interfaces:**
- Consumes: `MarketSnapshot`, `FVGEvent`, `LaneState`, `TradeIntent`.
- Produces: `EvaluateLaneA_V217Control(...)`, `EvaluateLaneB_ControlledFVG(...)`, `EvaluateLaneC_IFVG(...)`.

- [ ] **Step 1: Write failing tests** asserting Lane A retains permissive original-direction FVG behavior and repeated participation; Lane B enforces bounded re-entry/cooldown/quarantine; Lane C cannot reverse until invalidation plus opposite-side retest and rejection.
- [ ] **Step 2: Run the tests** and verify failure on missing lane evaluators.
- [ ] **Step 3: Implement Lane A** as the frozen V2.17-style control with its own repeat-entry attribution and designated V2.17 exit family.
- [ ] **Step 4: Implement Lane B** with max controlled re-entries, cooldown, and same-zone loss quarantine.
- [ ] **Step 5: Implement Lane C** with invalidation→IFVG→retest→rejection sequencing only.
- [ ] **Step 6: Run core-lane tests** and verify PASS.
- [ ] **Step 7: Commit** with `feat(v11): implement v217 control controlled-fvg and ifvg lanes`.

### Task 6: Context Feature Modules and Lanes D–H

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_context_lanes.py`

**Interfaces:**
- Consumes: `MarketSnapshot`, `FVGEvent`, `LaneState`.
- Produces: `VWAPFeatures`, `EMARegimeFeatures`, `LiquidityFeatures`, `AMDFeatures`, `EvaluateLaneD_VWAP(...)` through `EvaluateLaneH_FullHybrid(...)`.

- [ ] **Step 1: Write failing tests** verifying VWAP/profile, EMA100, liquidity/MSS/BOS, and AMD contribute score fields and do not silently hard-block unless the lane definition explicitly requires it.
- [ ] **Step 2: Run the tests** and verify failure on missing feature modules.
- [ ] **Step 3: Implement VWAP/profile extraction** with valid/invalid flags and score contribution.
- [ ] **Step 4: Implement EMA100/M15 regime extraction** with price-side and slope fields.
- [ ] **Step 5: Implement liquidity/structure extraction** for sweep, local swing, MSS/BOS, prior-high/low interaction.
- [ ] **Step 6: Implement AMD classification** returning accumulation/manipulation/distribution/unknown plus confidence.
- [ ] **Step 7: Implement Lanes D–H** using predefined weighted score combinations from the embedded configs.
- [ ] **Step 8: Run context-lane tests** and verify PASS.
- [ ] **Step 9: Commit** with `feat(v11): add context feature lanes and full hybrid scoring`.

### Task 7: Session Classification and Dedicated London/NY Lanes I–J

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_sessions.py`

**Interfaces:**
- Consumes: `MarketSnapshot`, base FVG evaluator.
- Produces: `ENUM_SESSION_BUCKET ClassifySession(datetime)`, `EvaluateLaneI_London(...)`, `EvaluateLaneJ_NewYork(...)`.

- [ ] **Step 1: Write failing tests** for Asia, London, overlap, New York, and rollover/other buckets, including boundary timestamps and cross-midnight behavior.
- [ ] **Step 2: Run tests** and verify failure.
- [ ] **Step 3: Implement deterministic session classification** using embedded server-time windows and explicit overlap precedence.
- [ ] **Step 4: Implement London and New York lane evaluators** using the same base alpha but enforcing their respective session windows.
- [ ] **Step 5: Run session tests** and verify PASS.
- [ ] **Step 6: Commit** with `feat(v11): add session research lanes`.

### Task 8: Exit Families, Re-entry Attribution, and Per-Lane Statistics

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_stats_and_exits.py`

**Interfaces:**
- Consumes: `LaneState`, `ShadowPosition`, `MarketSnapshot`.
- Produces: `ApplyExitFamily(...)`, exit families `EXIT_V217_TRAIL`, `EXIT_FIXED_R`, `EXIT_MFE_GIVEBACK`; per-lane first/second/third-plus entry stats; long/short/session stats.

- [ ] **Step 1: Write failing tests** for staged-lock + 0.10 ATR trail, fixed-R baseline, MFE giveback, hold-time accounting, first/second/third+ attribution, long/short PF, and session stats.
- [ ] **Step 2: Run tests** and verify failure.
- [ ] **Step 3: Implement the three predefined exit families** without combinatorial optimization.
- [ ] **Step 4: Implement all aggregate statistics** required by the spec including gross profit/loss, PF, WR, expectancy R, DD proxy, average MFE/MAE/hold, direction/session/re-entry breakdowns.
- [ ] **Step 5: Run tests** and verify PASS.
- [ ] **Step 6: Commit** with `feat(v11): add exit families and lane performance attribution`.

### Task 9: Telemetry, Sample Gates, Ranking, and OnTester Score

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_leaderboard.py`

**Interfaces:**
- Consumes: all `LaneStats` and completed trade records.
- Produces: `WriteTradeTelemetry(...)`, `WriteLeaderboardCsv()`, `SampleClass(int trades)`, `LaneRankScore(const LaneStats&)`, `PrintLeaderboard()`, `double OnTester()`.

- [ ] **Step 1: Write failing tests** for sample classes `<30`, `30–99`, `100–499`, `>=500`; leaderboard ordering with positive-expectancy priority, PF, DD penalty, sample-size gate, and stability penalty; insufficient-sample PF cannot outrank a usable positive-expectancy lane solely on PF.
- [ ] **Step 2: Run tests** and verify failure.
- [ ] **Step 3: Implement lane-qualified trade CSV** with all required fields and build id.
- [ ] **Step 4: Implement final leaderboard CSV and Journal table** with insufficient/exploratory/usable/strong labels.
- [ ] **Step 5: Implement `OnTester()`** returning the designated champion/composite research score without modifying parameters.
- [ ] **Step 6: Run leaderboard tests** and verify PASS.
- [ ] **Step 7: Commit** with `feat(v11): add autonomous leaderboard telemetry and tester score`.

### Task 10: End-to-End Tick Loop and Lane Orchestration

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`
- Create: `tests/v11/test_v11_orchestration_contract.py`

**Interfaces:**
- Consumes: all Tasks 1–9 interfaces.
- Produces: final `OnTick()`, `OnDeinit()`, optional `RunRealTesterSanityLane()` disabled by default.

- [ ] **Step 1: Write failing orchestration tests** verifying one snapshot per tick/bar cycle, all ten lanes are evaluated, each open lane is updated before new intents, no lane skips full-period shadow execution because another lane fails, and real tester execution is disabled by default.
- [ ] **Step 2: Run tests** and verify failure.
- [ ] **Step 3: Implement the final orchestration loop** with shared snapshot creation, lifecycle update, ten lane updates/evaluations, telemetry, and end-of-test export.
- [ ] **Step 4: Run orchestration tests** and verify PASS.
- [ ] **Step 5: Commit** with `feat(v11): orchestrate autonomous multi-lane research pass`.

### Task 11: Compile-Safety and Static Regression Gate

**Files:**
- Modify: `mt5/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5` only if required by failures.
- Create: `tests/v11/test_v11_static_regression.py`

**Interfaces:**
- Consumes: final V11 source.
- Produces: static evidence package suitable for native MetaEditor compile.

- [ ] **Step 1: Add static regression tests** for balanced delimiters, no `ArraySetAsSeries()` on static arrays, no duplicate function names, no unresolved C3/C4 identifiers, all ten lane names present exactly once in config initialization, unique telemetry names, and exact build identity.
- [ ] **Step 2: Run the complete Python contract suite** with `python -m pytest tests/v11 -v` and require all tests PASS.
- [ ] **Step 3: If native MetaEditor is available, compile** and require `0 errors`; resolve warnings that indicate correctness or portability problems.
- [ ] **Step 4: If native MetaEditor is unavailable, record that compile certification is pending** and do not claim native compile success.
- [ ] **Step 5: Commit** with `test(v11): complete compile-safety and static regression gate`.

### Task 12: Candidate-1 Artifact and Benchmark Runbook

**Files:**
- Create: `docs/testing/V11_CANDIDATE1_BENCHMARK.md`
- Export/copy final user artifact: `/mnt/data/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`

**Interfaces:**
- Consumes: final V11 source and test results.
- Produces: downloadable Candidate-1 `.mq5` and exact zero-config benchmark instructions.

- [ ] **Step 1: Write the benchmark runbook** with exactly: XAUUSD, M1, Every tick based on real ticks, 2026-01-01 to 2026-10-02, $10,000, 1:100, defaults untouched.
- [ ] **Step 2: Verify the EA banner/build id and telemetry filenames match the runbook**.
- [ ] **Step 3: Verify the full test suite one final time** and capture the command/result.
- [ ] **Step 4: Copy/export the exact tested source to `/mnt/data/AUREON_OMEGA_V11_AUTONOMOUS_RESEARCH_CHAMPION.mq5`** and compute SHA-256.
- [ ] **Step 5: Commit** with `docs(v11): add candidate1 benchmark runbook`.

## Self-Review Result

- Spec coverage: all 25 spec sections map to Tasks 1–12; no uncovered requirement found.
- Interface consistency: market snapshot → lane state → shadow execution → lane evaluators → statistics → leaderboard → orchestration is consistent across tasks.
- Review-focus coverage: lane isolation, look-ahead, fill realism, sample-size ranking, and build identity each have an explicit test owner.
- Scope discipline: Candidate 1 deliberately excludes self-optimization, LIVE execution, external AI/API calls, martingale/grid, and brute-force parameter search.
- Candidate-1 acceptance remains research throughput and attribution, not headline profit.
