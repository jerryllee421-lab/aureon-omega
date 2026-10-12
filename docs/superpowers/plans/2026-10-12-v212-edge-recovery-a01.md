# AUREON Ω V2.12 Edge Recovery A01 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a causal, fixed-risk V2.12 research lane that preserves the frozen MT5 control, reproduces its mechanism semantics as closely as M1 bid/ask bars permit, and runs the first A01 FVG-zone recycling attribution experiment with auditable R-space evidence.

**Architecture:** Keep every frozen V2.12 EA/preset/baseline file immutable. Add a separate causal Python simulator derived from `research/fvg_v211.py`, but remove same-bar lookahead by making every entry decision from fully closed information and entering no earlier than the next bar. Add stable FVG identity, attempt telemetry, fixed-risk R-space accounting, then run four predeclared A01 recycling policies on the pinned bid/ask M1 mirror. The fast lane is screening evidence only; MT5 real-tick Gate 0 remains promotion authority.

**Tech Stack:** Python 3.13; pandas/numpy/pyarrow/PyYAML/scipy from `research/requirements.txt`; pytest added only to the research CI command; GitHub Actions; existing pinned XAUUSD bid/ask mirror; existing PRIME Evolution policy.

**Spec:** `docs/superpowers/specs/2026-10-11-v212-edge-recovery-design.md`

## Global Constraints

- Never modify `ea/baseline/FVG_Scalper_V2_12_Research.mq5`, `ea/baseline/presets/FVG_V2_12_R943K.set`, `research/baselines/fvg_v212_r943k.json`, or `research/baselines/fvg_v212_r1_253b_historical.json`.
- LIVE execution remains prohibited; all outputs are research evidence only.
- Auto-compounding is OFF for A01 attribution; promotion is based on R-space edge, not terminal currency balance.
- A challenger may change at most two causal variables from its parent.
- Fast-lane results must be labeled `M1_BAR_APPROX_CAUSAL_NEXT_BAR_ENTRY`, never MT5 real-tick parity.
- Dataset source stays pinned to `kevingtlin/Market-Data-Lab` commit `922f83a60cc574e7395fb27397077288055a1ef6` unless a later explicitly versioned dataset replaces it.
- Historical periods already inspected are diagnostic/development evidence, not an untouched final holdout.
- Gate 0 before any promotion remains PXBT DEMO/research + MT5 Strategy Tester + Every tick based on real ticks + exact frozen source/preset + 2026-09-01 through 2026-09-24.
- If native broker history is unavailable, the native gate returns `DATA_INCOMPLETE`; generated ticks or substituted periods are forbidden.

## Review Focus

- **Lookahead risk:** rejection/FVG/ATR values used for an entry must come from bars closed before the entry timestamp; tests in Task 2 pin this.
- **Zone identity drift:** the same FVG must retain one stable ID across repeated attempts, while a genuinely newer zone must receive a new ID; tests in Task 3 pin this.
- **Re-entry pathology:** one-trade, cooldown, and attempt-cap policies must differ only in the declared recycling rule; tests in Task 3 pin this.
- **Exit ordering ambiguity:** if SL and TP are both touched in one M1 bar, the simulator must resolve conservatively to SL, and lock/trail changes only become active on the next bar; tests in Task 4 pin this.
- **False promotion from seen history:** A01 may rank/diagnose mechanisms on known history but must not label any result an untouched holdout or native-parity pass; tests in Task 6 pin output labels and promotion state.

---

### Task 1: Frozen-Control Identity Manifest

**Files:**
- Create: `research/v212_control_manifest.py`
- Create: `research/tests/test_v212_control_manifest.py`
- Modify: `.github/workflows/v212-control-integrity.yml`

**Interfaces:**
- Produces: `parse_set(path: Path) -> dict[str, str]`
- Produces: `sha256_file(path: Path) -> str`
- Produces: `build_manifest(repo_root: Path) -> dict[str, object]`
- Produces CLI: `python research/v212_control_manifest.py --out <path>`

- [ ] **Step 1: Write failing tests for canonical preset values and immutable evidence metadata**

Assert at minimum: `InpOneTradePerFVG=false`, `InpCooldownSeconds=0`, `InpRequireRejection=true`, `InpMinFVG_ATR=0.15`, `InpMinBody_ATR=0.5`, `InpUseProfitLock=true`, `InpUseATRTrail=true`, `InpTrail_ATR=0.1`, baseline role `FROZEN_CONTROL`, native model `Every tick based on real ticks`, and `live_ready=false`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest research/tests/test_v212_control_manifest.py -v`
Expected: FAIL because `research.v212_control_manifest` does not exist.

- [ ] **Step 3: Implement the manifest helper**

`build_manifest()` must include source EA SHA-256, preset SHA-256, R943K baseline SHA-256, R1.253B evidence SHA-256, benchmark metrics, native-reproduction status `PENDING`, `live_ready: false`, and `real_money_execution: LOCKED`.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `python -m pytest research/tests/test_v212_control_manifest.py -v`
Expected: PASS.

- [ ] **Step 5: Replace duplicated hash-building in the integrity workflow with a call to the helper while preserving all existing frozen-value assertions**

The workflow must still fail if any expected preset value or immutable baseline policy changes.

- [ ] **Step 6: Commit**

```bash
git add research/v212_control_manifest.py research/tests/test_v212_control_manifest.py .github/workflows/v212-control-integrity.yml
git commit -m "test: harden V2.12 frozen control identity"
```

---

### Task 2: Causal V2.12 FVG and Rejection Primitives

**Files:**
- Create: `research/fvg_v212_edge_recovery.py`
- Create: `research/tests/test_fvg_v212_edge_recovery.py`
- Reference only: `research/fvg_v211.py`

**Interfaces:**
- Produces dataclasses: `Params`, `Zone`, `Trade`
- Produces: `prepare(df: pd.DataFrame, p: Params) -> pd.DataFrame`
- Produces: `find_newest_fvg(x: pd.DataFrame, decision_i: int, p: Params) -> Zone | None`
- Produces: `rejection_ok(x: pd.DataFrame, decision_i: int, bullish: bool) -> tuple[bool, float]`

- [ ] **Step 1: Write failing synthetic-bar tests for bullish FVG, bearish FVG, minimum gap ATR, minimum body ATR/body ratio, and zone invalidation**

The control center values are `MinFVG_ATR=0.15`, `MinBody_ATR=0.50`, `MinBodyRatio=0.60`, `MaxFVG_Bars=1000`.

- [ ] **Step 2: Add a causality regression test**

Create two datasets identical through bar `i-1` but radically different at bar `i`; assert the entry decision prepared for bar `i` is identical in both datasets. This explicitly forbids same-bar future OHLC from affecting the decision.

- [ ] **Step 3: Run the tests and verify RED**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'fvg or causal or rejection' -v`
Expected: FAIL because the new simulator is not implemented.

- [ ] **Step 4: Implement causal feature timing**

ATR and any context consumed for an entry at bar `i` must be computed from data available through `i-1`. FVG formation may use the completed three-bar pattern ending at `i-1`. Rejection is evaluated on the completed bar `i-1`; entry is no earlier than bar `i` using bid/ask open. This is deliberately conservative and must be labeled as bar approximation rather than native parity.

- [ ] **Step 5: Run the tests and verify GREEN**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'fvg or causal or rejection' -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add research/fvg_v212_edge_recovery.py research/tests/test_fvg_v212_edge_recovery.py
git commit -m "feat: add causal V2.12 FVG research primitives"
```

---

### Task 3: Stable Zone Identity and A01 Recycling Policies

**Files:**
- Modify: `research/fvg_v212_edge_recovery.py`
- Modify: `research/tests/test_fvg_v212_edge_recovery.py`

**Interfaces:**
- `Zone` adds: `zone_id: str`, `attempts: int`, `last_entry_i: int | None`
- `Params` adds: `cooldown_bars: int = 0`, `max_attempts_per_fvg: int | None = None`
- Produces: `zone_identity(bullish: bool, formed_time: pd.Timestamp, low: float, high: float) -> str`
- Produces: `reentry_allowed(zone: Zone, entry_i: int, p: Params) -> bool`

- [ ] **Step 1: Write failing identity/re-entry tests**

Assert: same formed timestamp/direction/bounds gives identical ID; new formed timestamp gives a different ID; one-trade policy rejects attempt 2; 1-bar cooldown rejects immediate next-bar re-entry; max-attempt cap 3 rejects attempt 4; control allows repeated attempts with zero cooldown.

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'zone or reentry' -v`
Expected: FAIL.

- [ ] **Step 3: Implement A01 policy state**

Predeclare exactly four policies:

- `A01_CONTROL`: repeated entries, `cooldown_bars=0`, unlimited attempts.
- `A01_ONE_TRADE`: one trade per FVG.
- `A01_COOLDOWN_1BAR`: repeated entries, `cooldown_bars=1`, unlimited attempts.
- `A01_MAX3`: repeated entries, zero cooldown, `max_attempts_per_fvg=3`.

No other strategy variable changes between these variants.

- [ ] **Step 4: Run and verify GREEN**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'zone or reentry' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add research/fvg_v212_edge_recovery.py research/tests/test_fvg_v212_edge_recovery.py
git commit -m "feat: add V2.12 FVG recycling policies"
```

---

### Task 4: Historical Profit-Lock and ATR-Trail State Machine

**Files:**
- Modify: `research/fvg_v212_edge_recovery.py`
- Modify: `research/tests/test_fvg_v212_edge_recovery.py`

**Interfaces:**
- Produces: `next_stop_after_closed_bar(position: dict, mark: float, atr: float, bullish: bool, p: Params) -> float`
- `Trade` records: `mfe_r`, `mae_r`, `exit_reason`, `hold_bars`

- [ ] **Step 1: Write failing exit-state tests**

Pin the control behavior: 0.5R enables +0.1R protection; 1.0R enables +0.35R; 1.5R enables ATR trail at 0.10 ATR; a stop may only tighten, never loosen; if both stop and target touch within one bar, resolve to stop; a lock/trail calculated from bar `i` is effective from bar `i+1` only.

- [ ] **Step 2: Run and verify RED**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'lock or trail or stop' -v`
Expected: FAIL.

- [ ] **Step 3: Implement the state machine with fixed-risk accounting**

Keep nominal target at 30R for comparability. Do not compound. MFE/MAE are measured relative to initial risk and use side-correct bid/ask extremes.

- [ ] **Step 4: Run and verify GREEN**

Run: `python -m pytest research/tests/test_fvg_v212_edge_recovery.py -k 'lock or trail or stop' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add research/fvg_v212_edge_recovery.py research/tests/test_fvg_v212_edge_recovery.py
git commit -m "feat: reproduce V2.12 harvest state machine"
```

---

### Task 5: Fixed-Risk Simulator and Attempt Telemetry

**Files:**
- Modify: `research/fvg_v212_edge_recovery.py`
- Create: `research/tests/test_v212_a01_metrics.py`

**Interfaces:**
- Produces: `run(df: pd.DataFrame, p: Params) -> tuple[list[Trade], dict[str, object]]`
- Produces: `trades_frame(trades: list[Trade]) -> pd.DataFrame`
- Produces: `metrics(trades: list[Trade]) -> dict[str, object]`

`Trade` must include: `zone_id`, `attempt_no`, `time_since_prior_attempt_bars`, `fvg_age_bars`, `fvg_width_atr`, `fill_depth`, `rejection_strength`, `direction`, `entry_time`, `exit_time`, `realized_r`, `mfe_r`, `mae_r`, `exit_reason`, `entry_spread`.

- [ ] **Step 1: Write failing metrics tests**

For a small deterministic trade fixture, assert exact trade count, win rate, PF, expectancy R, net R, average win/loss R, max DD R, longest losing streak, and attempt-number grouping.

- [ ] **Step 2: Add bid/ask direction tests**

Long entry uses ask, long exit uses bid; short entry uses bid, short exit uses ask. Spread must therefore affect realized R naturally and must not be subtracted a second time.

- [ ] **Step 3: Run and verify RED**

Run: `python -m pytest research/tests/test_v212_a01_metrics.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the simulator and telemetry**

The output fidelity field is exactly `M1_BAR_APPROX_CAUSAL_NEXT_BAR_ENTRY`. The report must explicitly state that intrabar MT5 rejection/tick sequencing, broker margin, stop/freeze levels and lot rounding are not reproduced.

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m pytest research/tests/test_v212_a01_metrics.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add research/fvg_v212_edge_recovery.py research/tests/test_v212_a01_metrics.py
git commit -m "feat: add fixed-R V2.12 A01 simulator telemetry"
```

---

### Task 6: A01 Attribution Runner and Research Report

**Files:**
- Create: `research/run_v212_a01.py`
- Create: `research/tests/test_run_v212_a01.py`
- Reference: `research/mirror_m1.py`
- Reference: `research/evolution/policy.yml`

**Interfaces:**
- Produces CLI: `python research/run_v212_a01.py --data <parquet-or-root> --manifest <download_manifest.json> --out <dir>`
- Produces files: `comparison.csv`, `trades_<variant>.csv`, `attempt_breakdown.csv`, `year_breakdown.csv`, `direction_breakdown.csv`, `exit_breakdown.csv`, `attribution.json`, `provenance.json`

- [ ] **Step 1: Write failing report-contract tests**

Assert all four predeclared A01 variants are present; no extra strategy parameter differs between variants; every report carries dataset hash, code/config provenance placeholder, period, fidelity class, source commit, and `native_parity_status: PENDING`.

- [ ] **Step 2: Add anti-false-holdout tests**

Assert report labels 2016 through the pinned mirror endpoint as `historical_diagnostic`/rolling research data and does not emit `untouched_holdout_pass`. Final promotion must remain blocked until native Gate 0 plus genuinely external 2026 data exist.

- [ ] **Step 3: Run and verify RED**

Run: `python -m pytest research/tests/test_run_v212_a01.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the A01 runner**

Primary attribution output must answer: expectancy/PF/net-R by attempt number and variant; how many zones produce attempts 1, 2, 3, 4+; whether later attempts add or destroy edge; whether a cooldown or cap improves fixed-risk edge without collapsing opportunity count.

- [ ] **Step 5: Integrate the existing PRIME policy as a diagnostic classifier only**

Do not modify `research/evolution/policy.yml`. A01 results may be classified against its minimum PF/expectancy/sample rules, but classification must remain `RESEARCH_ONLY` until native and external-holdout gates pass.

- [ ] **Step 6: Run and verify GREEN**

Run: `python -m pytest research/tests/test_run_v212_a01.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add research/run_v212_a01.py research/tests/test_run_v212_a01.py
git commit -m "feat: add V2.12 A01 recycling attribution runner"
```

---

### Task 7: GitHub Actions A01 Tournament

**Files:**
- Create: `.github/workflows/v212-edge-recovery-a01.yml`
- Create: `research/requests/v212-a01-edge-recovery-20261012.json`

**Interfaces:**
- Workflow artifact name prefix: `AUREON-V212-A01-EDGE-RECOVERY`
- Uses existing `research/mirror_m1.py` and pinned commit `922f83a60cc574e7395fb27397077288055a1ef6`.

- [ ] **Step 1: Create workflow with separate `tests` and `a01` stages**

`tests` installs `research/requirements.txt` plus pytest, runs all new V2.12 tests, and must pass before `a01` executes.

- [ ] **Step 2: Configure bounded historical research data**

Use M1 bid/ask data from the pinned mirror through its verified endpoint. Preserve `download_manifest.json`; do not call the data an untouched holdout.

- [ ] **Step 3: Run A01 and package evidence**

Artifact must contain test output, control manifest, dataset manifest, comparison/attribution CSV/JSON, source commit, request JSON, and full provenance.

- [ ] **Step 4: Add fail-closed assertions**

Workflow fails if frozen-control manifest check fails, dataset hash/provenance is missing, any variant is absent, tests fail, or output fidelity/native-status labels are incorrect.

- [ ] **Step 5: Commit the request last so the push can trigger the tournament on the research branch**

```bash
git add .github/workflows/v212-edge-recovery-a01.yml
git commit -m "ci: add V2.12 A01 edge recovery tournament"
git add research/requests/v212-a01-edge-recovery-20261012.json
git commit -m "research: trigger V2.12 A01 edge recovery"
```

---

### Task 8: Evidence Review and A02 Decision Gate

**Files:**
- Create after run: `research/evolution/decisions/v212_a01_<run-id>.json`
- Update only after evidence: `research/evolution/campaigns/fvg_v212_mechanism_attribution.json`

**Interfaces:**
- Produces decision status: one of `A01_EDGE_CONFIRMED`, `A01_CONTROLLED_RECYCLING_PREFERRED`, `A01_RECYCLING_REJECTED`, `A01_ENGINE_PARITY_INSUFFICIENT`.

- [ ] **Step 1: Verify artifact provenance and deterministic rerun agreement before interpreting performance**

A second run with identical data/config must reproduce trade identities and aggregate R-space metrics exactly.

- [ ] **Step 2: Compare A01 variants without using terminal currency balance**

Primary metrics: PF, expectancy R, net R, max DD R, trade/zone counts, attempt-number expectancy, year/direction stability, MFE/MAE, and exit reasons.

- [ ] **Step 3: Apply the stop rule**

If the causal fast lane is materially negative across all four variants or its mechanism behavior cannot be reconciled with the historical control, classify `A01_ENGINE_PARITY_INSUFFICIENT` and diagnose fidelity before moving to A02. Do not tune around the failure.

- [ ] **Step 4: Advance only with evidence**

If repeated recycling contributes stable incremental edge, retain it. If later attempts are destructive, choose the simplest bounded recycling rule supported by attempt-number evidence. Only then write a separate A02 rejection-attribution implementation plan.

- [ ] **Step 5: Commit the decision record**

```bash
git add research/evolution/decisions/v212_a01_*.json research/evolution/campaigns/fvg_v212_mechanism_attribution.json
git commit -m "research: record V2.12 A01 recycling decision"
```

---

## Self-Review Result

- Spec coverage: this plan implements the approved first build slice and A01 only; A02-A07 are intentionally deferred until A01 evidence exists.
- Causality: same-bar lookahead in the old proxy is explicitly prevented by Task 2 regression tests.
- Frozen control: no baseline EA/preset/benchmark content is modified; Task 1 only verifies and hashes them.
- Research fidelity: bar approximation remains explicitly non-native; Gate 0 is not bypassed.
- Risk/selection: compounding is disabled and no unseen final holdout is claimed.
- Execution: no broker order mutation and no LIVE path is introduced.
