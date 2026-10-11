# AUREON Ω V2.12 Benchmark Edge Recovery — Design

Date: 2026-10-11
Branch: `research/v212-edge-recovery-20261011`
Status: DESIGN FOR REVIEW

## 1. Mission

Build directly on the preserved `FVG_Scalper_V2_12_Research` benchmark lineage and determine which mechanisms produced the historical high-growth results before attempting any improvement.

The historical R1.253B tester record and the R943K control are evidence anchors, not forward-performance forecasts. The frozen baseline EA, canonical preset, and benchmark records remain immutable.

The mission is successful only if a challenger demonstrates a robust positive edge in normalized R-space, survives realistic costs and robustness tests, reproduces materially under native MT5 real ticks, and then passes a genuinely external 2026 holdout before DEMO-forward consideration.

LIVE execution remains prohibited throughout this campaign.

## 2. Evidence anchors

### Historical high-growth benchmark

Preserve `research/baselines/fvg_v212_r1_253b_historical.json` as immutable historical evidence.

Recorded characteristics:

- source family: `FVG_Scalper_V2_12_Research`;
- 18,368 trades;
- 68.06% win rate;
- profit factor 2.48;
- Sharpe 36.36;
- average hold approximately 1m25s;
- M1 entry and M1 bias timeframe;
- bias filter OFF;
- midpoint filter OFF;
- rejection required;
- `MinFVG_ATR=0.15`;
- `MinBody_ATR=0.50`;
- repeated FVG trading enabled;
- zero cooldown;
- 24-hour scanning;
- profit locks at 0.5R -> +0.1R and 1.0R -> +0.35R;
- ATR trailing from 1.5R with 0.10 ATR distance;
- requested risk 2%, effective hard cap 1.25%;
- auto-compounding enabled in the historical currency result.

### Frozen native control

Preserve without mutation:

- `ea/baseline/FVG_Scalper_V2_12_Research.mq5`;
- `ea/baseline/presets/FVG_V2_12_R943K.set`;
- `research/baselines/fvg_v212_r943k.json`;
- `research/config/fvg_v212_control.yml`.

The existing integrity workflow remains authoritative for detecting accidental control drift.

## 3. Core hypothesis

The historical edge did not primarily come from a large indicator stack. The leading causal hypothesis is the interaction of:

1. FVG identification on M1;
2. rejection confirmation;
3. displacement/FVG quality thresholds;
4. repeated exploitation of a still-valid FVG;
5. zero or near-zero recycle delay;
6. rapid profit locking;
7. tight ATR trailing;
8. high opportunity throughput;
9. compounding applied only after a positive trade-level edge existed.

The campaign must test these mechanisms independently rather than assume the hypothesis is correct.

## 4. Research principles

### Immutable ancestor

No experiment may modify the frozen V2.12 files. Every challenger must live under a separate research path and identify its parent.

### Maximum causal mutation

A single challenger may change at most two causal variables from its parent. Bundled feature additions are prohibited unless every component has already survived ablation independently.

### Edge before compounding

During mechanism attribution and candidate selection:

- auto-compounding is OFF;
- results are evaluated primarily in R-space;
- position sizing cannot promote a strategy;
- terminal currency balance is diagnostic only.

Compounding may be reintroduced only after the trade-level edge has passed robustness and native-parity gates.

### Causality

No decision may use future information. Features available at an entry decision must come only from completed information available at that timestamp. Higher-timeframe values must use closed higher-timeframe candles.

### Broker-side truth

Bid/ask direction, spread, tick size, tick value, contract size, stop/freeze levels, volume step, and margin constraints must come from broker metadata in native parity code when available. Missing or invalid symbol properties fail closed.

## 5. Gate 0 — exact control reproduction

Before improvement experiments are eligible for promotion, the Dome must attempt an exact broker-native reproduction of the frozen control.

Required contract:

- XAUUSD;
- PXBT DEMO/research account context only;
- MT5 Strategy Tester;
- Every tick based on real ticks;
- exact frozen EA and preset;
- benchmark window `2026-09-01` through `2026-09-24` for the R943K control;
- no parameter mutation;
- preserve report, journal/tester logs, EA hash, preset hash, symbol specification snapshot and MT5 build information.

If required broker history is unavailable, return `DATA_INCOMPLETE`; do not silently substitute generated ticks or a different period.

A failed external proxy cannot invalidate the frozen broker-native benchmark. Conversely, an unreproduced historical benchmark cannot be treated as validated forward evidence.

## 6. Fast research lane

A deterministic Python research lane may use pinned historical bid/ask M1 data for inexpensive causal screening.

Every result must state its fidelity explicitly. Bar approximation cannot be labeled MT5 real-tick parity.

The fast lane must record:

- dataset source and commit/hash;
- code commit/hash;
- start/end timestamps;
- bid/ask construction;
- spread model;
- commission model;
- slippage model;
- symbol assumptions;
- configuration hash;
- fidelity label.

Its purpose is to reject weak hypotheses cheaply and rank survivors for native testing.

## 7. Experiment sequence

### A01 — FVG zone recycling

Primary question: was repeated exploitation of the same valid FVG a major source of edge?

Predeclared variants:

- Control: repeated entries, zero cooldown;
- A01-B: one trade per FVG;
- A01-C: repeated entries with bounded cooldown;
- A01-D: repeated entries with a maximum-attempt cap per FVG.

Mandatory telemetry:

- stable FVG event ID;
- attempt number within FVG;
- time since prior attempt;
- FVG age;
- FVG width/ATR;
- fill depth;
- rejection strength;
- MFE/MAE;
- realized R;
- exit reason.

Rank expectancy by attempt number. If later attempts are systematically destructive, the improvement path is controlled recycling rather than disabling recycling globally.

### A02 — rejection attribution

Compare canonical rejection-required behavior against rejection disabled, with all other causal variables held fixed.

Measure:

- expectancy R;
- PF;
- adverse excursion;
- favorable excursion;
- stop rate;
- attempt-number interaction.

If rejection adds edge, retain it and investigate calibrated rejection strength only after the binary attribution is complete.

### A03 — FVG/displacement neighborhood

Test a small predeclared local neighborhood around the control values rather than a broad optimizer search.

Initial lattice:

- `MinFVG_ATR`: 0.10, 0.15, 0.20;
- `MinBody_ATR`: 0.40, 0.50, 0.60.

`0.15 / 0.50` is the center/control point.

Promotion requires a stable neighborhood or plateau. A single isolated best cell is classified as a parameter cliff and rejected.

### A04 — direction attribution

Compare long-only, short-only and combined behavior after A01-A03 establish the mechanism baseline.

No side may be disabled solely because of one profitable historical period. Directional changes require persistence across rolling windows.

### A05 — exit engine attribution

Test the historical harvesting machinery directly.

Predeclared comparisons:

- full historical lock + trail;
- profit locks OFF, ATR trail ON;
- profit locks ON, ATR trail OFF;
- both OFF with fixed terminal target;
- local trailing-distance neighborhood around 0.10 ATR only if the historical trail proves useful.

Report realized-R distribution, MFE capture efficiency, give-back from MFE, stop-after-lock frequency, median hold time and tail-winner dependence.

### A06 — compounding attribution

Only after a positive fixed-risk edge is demonstrated, compare identical trade sequences with compounding OFF versus ON.

The purpose is to quantify amplification, not to use compounding to manufacture an apparent edge.

### A07 — execution stress

For surviving mechanisms, stress:

- spread expansion;
- slippage shocks;
- entry delay;
- exit delay;
- commission increase;
- broker stop/freeze constraints.

A candidate that becomes negative under small realistic execution perturbations is rejected as execution-sensitive.

## 8. Research splits

Historical periods already inspected by prior work are diagnostic data, not untouched final holdouts.

Use rolling development/validation windows for mechanism discovery and walk-forward selection.

Reserve new 2026 broker-native data that has not been used for candidate selection as the final external holdout. Final-holdout metrics must never influence candidate selection or parameter tuning.

## 9. Output schema

Every candidate and ablation must report at minimum:

- parent ID;
- mutation variables;
- configuration hash;
- data hash/provenance;
- fidelity class;
- trades;
- win rate;
- PF;
- expectancy R;
- net R;
- average win R;
- average loss R;
- max DD R and %;
- longest losing streak;
- MFE/MAE distribution;
- long/short breakdown;
- session/hour breakdown;
- year/month breakdown;
- FVG attempt-number breakdown;
- exit-reason breakdown;
- spread/slippage sensitivity;
- neighbor-stability result;
- walk-forward result;
- Monte Carlo/bootstrapped drawdown result;
- native-parity status.

## 10. Promotion gates

A candidate may advance from fast research into native testing only when all applicable gates pass:

- deterministic reproduction of its own results;
- sufficient sample size;
- positive expectancy R;
- PF >= 1.20 in the research policy minimum and preferably >= 1.30 before expensive native testing;
- positive repeated rolling validation windows rather than one profitable aggregate;
- no parameter cliff;
- no single year/month/session/side responsible for the majority of total edge;
- acceptable drawdown;
- acceptable spread/slippage/delay stress;
- no tail-winner dependency;
- mechanism survives ablation against its parent.

Champion promotion additionally requires:

- official MetaEditor compile at 0 errors and 0 warnings;
- MT5 Every tick based on real ticks evidence;
- representative trade-by-trade parity audit;
- positive genuinely external 2026 broker-native holdout;
- controlled DEMO forward validation and reconciliation.

No candidate is LIVE-ready as part of this mission.

## 11. First build slice

After this design is approved, implementation begins with a bounded research infrastructure slice rather than changing the EA directly:

1. strengthen frozen-control integrity checks and record exact source/preset hashes;
2. create deterministic unit tests for FVG identification, rejection semantics, displacement qualification and zone identity;
3. add attempt-number/re-entry telemetry in an independent research simulator;
4. reproduce the historical control logic with compounding disabled in R-space;
5. run A01 zone-recycling attribution first;
6. stop and diagnose if the fast engine cannot reproduce the expected mechanism behavior;
7. only then proceed to A02-A07 in order.

The historical baseline files remain untouched throughout.

## 12. Decision rule

The Research Dome is not trying to recreate R1.253B by curve fitting.

It is trying to recover the repeatable mechanism that generated the original PF/throughput profile, remove components that do not contribute, improve only mechanisms supported by causal evidence, and then prove the resulting edge under stricter execution and validation conditions than the historical test.
