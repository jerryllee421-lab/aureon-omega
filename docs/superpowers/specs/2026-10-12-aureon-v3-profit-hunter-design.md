# AUREON Ω V3 — PROFIT HUNTER
## Hybrid Heritage Monster — Formal Architecture & Research Specification

**Status:** REVIEW GATE  
**Date:** 2026-10-12  
**Primary market:** XAUUSD / Gold  
**Primary execution timeframe:** M1 precision with higher-timeframe context  
**Research mode:** fixed-size first, risk scaling only after raw edge validation  
**Execution target after certification:** MT5 DEMO only  
**LIVE trading:** PROHIBITED until a separate explicit authorization and a new certification gate  

---

## 1. Mission

AUREON Ω V3 Profit Hunter replaces the losing HFS V2 alpha engine while preserving the hardened execution, safety, telemetry, anti-churn, and evidence infrastructure developed in V2.

The system SHALL pursue the following objective:

> Find historically validated XAUUSD edge, enter at the highest-quality causal trigger, monetize favorable excursion aggressively, exit when the thesis or expected continuation degrades, then immediately hunt for a genuinely new independent opportunity.

V3 SHALL NOT attempt to manufacture profitability through leverage, compounding, martingale, grid recovery, or overfitted parameter selection.

The V2.17 FVG family is retained as the primary historical alpha control because it previously produced materially stronger backtest characteristics than the V2 score-based engine. That historical result is a benchmark, not proof of future profitability.

---

## 2. Binding Research Principles

1. **Alpha before sizing.** All strategy research begins with fixed 0.01 lot or risk-normalized fixed exposure.
2. **Causal data only.** No feature, higher-timeframe context, regime label, or exit decision may use information unavailable at the decision timestamp.
3. **Independent evidence.** Correlated indicators may support a specialist internally but SHALL NOT be repeatedly counted as independent confirmation.
4. **Strategy specialists compete.** FVG, iFVG, liquidity reversal, momentum, and pullback systems remain separately attributable.
5. **Long and short are independent policies.** Directional asymmetry is explicitly modeled.
6. **Execution economics are mandatory.** Spread, commission, slippage, and broker constraints are incorporated before entry.
7. **No automatic promotion.** Research success does not authorize DEMO or LIVE execution automatically.
8. **No fabricated data.** Missing ticks, spreads, volume, slippage, or symbol specifications remain missing and are explicitly labeled.
9. **Every change is falsifiable.** Every challenger must be tested against an unchanged control on identical data and execution assumptions.
10. **Profitability is never claimed from in-sample results alone.** Walk-forward and stress validation are mandatory.

---

## 3. System Architecture

```text
BROKER / HISTORICAL MARKET TRUTH
        ↓
DATA QUALITY + CAUSAL TIMESTAMP CONTRACT
        ↓
FEATURE FACTORY
        ↓
REGIME BRAIN
        ↓
ALPHA SPECIALIST BANK
 ├─ V2.17 FVG Heritage        [primary control]
 ├─ iFVG Flip                 [challenger]
 ├─ Liquidity Sweep + MSS     [challenger]
 ├─ Momentum Expansion        [research]
 └─ Trend Pullback            [research]
        ↓
ENTRY STATE MACHINE
 DETECTED → ARMED → TRIGGERED → CONFIRMED
        ↓
POST-COST EXPECTED-VALUE GATE
        ↓
LONG / SHORT POLICY
        ↓
IMMUTABLE TRADE INTENT
        ↓
SL + TP1 + TP2 + TP3 / RUNNER MAP
        ↓
PROFIT HUNTER POSITION MANAGER
        ↓
EXIT + RECONCILIATION
        ↓
6-SECOND ANTI-CHURN + FRESH-EVENT GATE
        ↓
EVIDENCE LEDGER
        ↓
HUNT AGAIN
```

The signal engine, risk governor, execution adapter, and evidence ledger are separate modules. Failure in one module SHALL NOT silently weaken another.

---

## 4. Preserved V2 Infrastructure

V3 SHALL preserve or improve the following V2 capabilities:

- 6-second anti-churn floor;
- fresh-event ID requirement;
- no same-tick close → immediate recycled re-entry;
- broker-valid protective SL;
- broker-side TP protection;
- daily loss governor;
- maximum drawdown governor;
- consecutive-loss guard;
- one-position default semantics for certification;
- spread gate;
- slippage telemetry;
- restart-safe state where supported;
- MFE / MAE telemetry;
- entry cost capture;
- exit reason attribution;
- immutable trade-level research ledger;
- fail-closed behavior on stale or invalid market state.

V3 SHALL NOT inherit the losing V2 additive score engine as authoritative alpha.

---

## 5. Feature Factory

The Feature Factory SHALL compute deterministic, timestamped features once per market update.

### 5.1 Structure

- HH / HL / LH / LL;
- BOS;
- MSS;
- displacement;
- swing highs/lows;
- compression / expansion;
- breakout distance normalized by ATR;
- candle body / ATR;
- body-to-range efficiency;
- wick asymmetry;
- range location.

### 5.2 Liquidity

- previous day high / low;
- previous week high / low;
- Asia, London, New York session highs/lows;
- equal highs / equal lows;
- local swing clusters;
- liquidity sweep;
- reclaim;
- stop-run distance normalized by ATR;
- room to next liquidity pool.

### 5.3 Price Delivery

- bullish / bearish FVG;
- iFVG flip;
- gap width / ATR;
- mitigation depth;
- zone age;
- repeated-touch count;
- displacement quality;
- rejection quality;
- order-block proxy where causally defined;
- premium / discount location.

### 5.4 Value / Volume Proxies

Where broker data supports them:

- rolling micro-VWAP;
- session VWAP;
- daily anchored VWAP;
- tick-volume anomaly;
- volume z-score;
- proxy POC / VAH / VAL only when data quality passes.

Any OTC volume-profile output MUST be labeled as a broker-volume proxy rather than centralized order flow.

### 5.5 Momentum / Trend

- EMA20 / EMA50 structure;
- EMA100 context;
- EMA200 context;
- slope normalized by ATR;
- velocity;
- acceleration;
- RSI / ADX / Stochastic only where research proves incremental value;
- realized volatility percentile;
- ATR percentile.

### 5.6 Execution Quality

- live / historical spread;
- spread percentile;
- spread / ATR;
- expected slippage class;
- quote velocity;
- spread shock;
- stop-distance viability;
- broker stops/freeze constraints;
- rollover / thin-liquidity state.

---

## 6. Regime Brain

Minimum regimes:

- TREND_EXPANSION;
- TREND_PULLBACK;
- BREAKOUT_TRANSITION;
- VOLATILITY_COMPRESSION;
- VOLATILITY_EXPANSION;
- RANGE;
- LIQUIDITY_REVERSAL;
- EXHAUSTION;
- CHAOTIC;
- TOXIC_EXECUTION;
- UNKNOWN / DEGRADED.

Regime classification is primarily a routing/ranking layer. A regime becomes a hard gate only when the associated specialist demonstrates robust out-of-sample benefit from that gate.

---

## 7. Alpha Specialist Bank

### 7.1 V2.17 FVG Heritage — Primary Control

Preserve the core research DNA:

- M1 FVG detection;
- displacement requirement;
- minimum body / ATR quality;
- minimum body efficiency;
- rejection-based interaction;
- optional repeated entries on a still-valid FVG;
- structural / ATR stop geometry;
- staged profit locking;
- ATR trailing candidate;
- FVG identity and telemetry.

V3 SHALL NOT blindly preserve:

- a universal 30R objective;
- zero cooldown;
- unlimited repeated same-zone entries;
- unrestricted compounding;
- assumptions that worked only in one broker/test period.

Those become explicit research candidates.

### 7.2 iFVG Flip Specialist

Candidate sequence:

1. valid FVG forms;
2. price violates / closes through the zone;
3. former FVG flips role;
4. structure confirms reversal or continuation;
5. retest / rejection triggers entry.

Every iFVG candidate receives a unique event ID.

### 7.3 Liquidity Sweep + MSS Specialist

Candidate sequence:

1. identifiable liquidity pool;
2. sweep beyond the pool;
3. reclaim;
4. MSS / BOS in the expected direction;
5. displacement;
6. retracement into FVG / value zone;
7. execution trigger.

A sweep without reclaim/MSS SHALL NOT be treated as a complete setup.

### 7.4 Momentum Expansion Specialist

Candidate sequence:

- prior compression;
- volatility expansion;
- directional displacement;
- favorable body / wick structure;
- sufficient room to target;
- post-cost EV positive.

### 7.5 Trend Pullback Specialist

Candidate sequence:

- established causal trend context;
- pullback into value / EMA / FVG confluence;
- loss of countertrend momentum;
- resumption trigger;
- target room confirmed.

---

## 8. Specialist Certification States

Every specialist has one state:

- `CONTROL` — preserved benchmark logic;
- `RESEARCH_ONLY` — can generate simulated signals and telemetry only;
- `RESEARCH_PASS` — passed initial fixed-size and walk-forward tests;
- `MT5_CERTIFIED` — native real-tick parity achieved;
- `DEMO_READY` — can participate in DEMO canary;
- `REJECTED` — failed promotion gates.

Only MT5-certified specialists may enter an execution-capable build.

---

## 9. Entry State Machine

Every candidate progresses through:

```text
DETECTED
  ↓
DEVELOPING
  ↓
ARMED
  ↓
TRIGGERED
  ↓
CONFIRMED
  ↓
EXECUTED
```

Possible terminal states before execution:

- INVALIDATED;
- EXPIRED;
- COST_BLOCKED;
- REGIME_BLOCKED;
- DUPLICATE_BLOCKED;
- DATA_BLOCKED.

### 9.1 Fresh Event Rule

An entry requires a new event identity relative to the most recently closed position.

An event ID SHALL incorporate enough context to prevent stale re-entry, such as:

- specialist;
- direction;
- setup formation time;
- zone / structure identity;
- meaningful price bucket where required.

### 9.2 Anti-Churn Rule

After a close:

- minimum temporal floor: 6 seconds;
- a new independent event is still required;
- the same closed-bar signal cannot be recycled merely because price has not changed materially.

The 6-second rule is a minimum control, not an entry signal.

---

## 10. Long / Short Policy Separation

Long and short research SHALL be evaluated independently for every specialist.

Independent parameters may include:

- minimum setup quality;
- displacement requirement;
- mitigation depth;
- stop geometry;
- target geometry;
- session compatibility;
- regime compatibility;
- expected hold duration;
- MFE/MAE profile;
- cost tolerance.

The system SHALL NOT force parameter symmetry between directions.

---

## 11. Post-Cost Expected-Value Gate

Before every entry, estimate:

```text
ExpectedGrossMove
− spread
− commission
− expected slippage
− execution buffer
= ExpectedNetMove
```

Where enough observations exist, estimate conditional expectancy from historical cohorts:

```text
EV = P(win) × AvgWin − P(loss) × AvgLoss − Costs
```

Conditioning dimensions may include:

- specialist;
- direction;
- regime;
- session;
- ATR percentile;
- spread percentile;
- setup quality band;
- mitigation depth;
- displacement class.

No candidate is admitted solely because a generic score exceeds a threshold.

---

## 12. Stop-Loss Architecture

Candidate stop families:

- FVG invalidation;
- sweep extreme;
- structural swing;
- breakout candle invalidation;
- ATR;
- structure + ATR buffer.

Research grid may include ATR buffers such as:

`0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 2.50`

Every stop must satisfy broker stop/freeze constraints in native certification.

A stop-distance cap may be tested, but cap activation MUST be logged and evaluated separately.

---

## 13. Profit Hunter Position Manager

The Profit Hunter is a specialist-aware state machine, not one universal trailing stop.

### 13.1 Position States

- MICRO;
- STANDARD;
- RUNNER;
- PROTECT;
- EXIT_PENDING.

Transitions are monotonic unless an explicit protection transition is defined.

### 13.2 MFE / MAE Intelligence

For every trade record:

- MFE in price, money, and R;
- MAE in price, money, and R;
- time to MFE;
- time to MAE;
- time to 0.25R / 0.5R / 1R / 1.5R / 2R / 3R;
- maximum achieved R;
- realized R;
- post-peak giveback;
- realized / MFE capture ratio.

### 13.3 Profit Capture Ratio

```text
PCR = Realized Favorable Profit / Maximum Favorable Excursion
```

PCR is evaluated by:

- specialist;
- direction;
- regime;
- session;
- exit reason;
- score / quality band;
- volatility band.

### 13.4 Target Families

Test:

- fixed R;
- ATR target;
- liquidity target;
- staged TP1 / TP2 / TP3;
- 100% single-exit;
- 50/50;
- 25/25/50;
- 33/33/34;
- runner extension.

No partial-exit template is assumed superior before testing.

### 13.5 Dynamic Protection

Candidates:

- cost-covered break-even;
- profit lock at empirically validated R thresholds;
- ATR trail;
- swing trail;
- EMA trail;
- momentum-decay exit;
- structure-failure exit;
- opposite-MSS exit;
- time-stop.

A dynamic exit may modify the broker TP/SL only when the modification remains broker-valid.

---

## 14. Failure-Trade Research

The previous V2 research showed the FAILURE exit cluster as a dominant loss source. V3 therefore requires explicit failure attribution.

Every losing / failure trade SHALL be classified where possible as:

- never achieved positive MFE;
- late entry;
- false breakout;
- wrong regime;
- adverse spread / cost;
- insufficient displacement;
- failed reclaim;
- wrong direction;
- poor stop geometry;
- premature failure exit;
- structurally invalidated;
- unknown.

The primary objective is to remove bad entries rather than merely hold losing trades longer.

---

## 15. Research Telemetry Schema

Minimum per-trade fields:

- experiment_id;
- strategy / specialist;
- event_id;
- direction;
- regime;
- signal_time;
- arm_time;
- trigger_time;
- entry_time;
- requested_entry;
- actual / simulated fill;
- spread;
- commission;
- slippage;
- latency where available;
- ATR and ATR percentile;
- setup quality;
- displacement quality;
- FVG / iFVG geometry;
- sweep / reclaim flags;
- MSS / BOS flags;
- VWAP context;
- session;
- stop family;
- SL;
- TP1;
- TP2;
- TP3;
- initial risk;
- MFE;
- MAE;
- time to MFE;
- maximum R;
- realized R;
- PCR;
- hold duration;
- exit reason;
- gross P&L;
- net P&L;
- data fidelity;
- code version;
- dataset version.

Research ledgers are append-only for a given experiment ID.

---

## 16. Alpha Tournament

The first V3 research campaign SHALL compare at minimum:

1. original V2.17 FVG control;
2. V2.17 + 6-second/fresh-event protection;
3. FVG + displacement-quality gate;
4. FVG + MSS confirmation;
5. FVG + liquidity context;
6. iFVG flip;
7. liquidity sweep + MSS;
8. momentum expansion;
9. trend pullback;
10. long-only / short-only variants of each meaningful candidate.

Each candidate reports:

- trades;
- net P&L;
- PF;
- expectancy;
- expectancy in R;
- WR;
- average win / loss;
- payoff ratio;
- max DD;
- recovery factor;
- MFE / MAE;
- PCR;
- yearly performance;
- session performance;
- direction performance;
- cost sensitivity.

Any candidate with persistently negative out-of-sample expectancy or OOS PF below 1.0 is rejected from executable V3 composition.

---

## 17. Exit Tournament

Only alpha candidates that survive the Alpha Tournament enter the Exit Tournament.

Compare:

- original V2.17 locks / trail;
- fixed-R targets;
- staged TP1/TP2/TP3;
- MFE-derived targets;
- ATR trail;
- swing / structure trail;
- momentum-decay exit;
- hybrid Profit Hunter.

The test SHALL distinguish:

- alpha improvement from entry selection;
- monetization improvement from exit management.

---

## 18. Decade Research Structure

Research dataset target:

**2016-01-01 through 2025-12-31**

This period has already been inspected during prior AUREON research and SHALL NOT be described as untouched.

### 18.1 Rolling Walk-Forward

Minimum outer tests:

- train through 2018 → test 2019;
- train through 2019 → test 2020;
- train through 2020 → test 2021;
- train through 2021 → test 2022;
- train through 2022 → test 2023;
- train through 2023 → test 2024;
- train through 2024 → test 2025.

Parameter selection occurs only inside earlier data.

Quarterly evaluation is required when trade counts are sufficient.

---

## 19. Robustness & Execution Torture

Every serious candidate SHALL be subjected to:

### 19.1 Cost Stress

- base spread / slippage / commission;
- 1.25× spread;
- 1.50× spread;
- 2.00× spread;
- 2× slippage;
- 3× slippage;
- higher commission scenario.

### 19.2 Delay / Fill Stress

- delayed entry;
- one-bar severe delay;
- missed fills 5% / 10% / 20%;
- adverse slippage tails.

### 19.3 Parameter Stability

At minimum:

- ±5%;
- ±10%;
- ±20% perturbations.

A candidate that depends on a narrow parameter spike fails robustness.

### 19.4 Placebo / Falsification

- inverted direction;
- random signal with same trade count;
- shuffled-time placebo;
- delayed-entry placebo;
- feature ablation;
- specialist ablation in hybrid builds.

---

## 20. Monte Carlo / Sequence Risk

After a candidate demonstrates positive raw edge:

- bootstrap / reorder completed trades;
- estimate 95% and 99% drawdown bands;
- loss-streak distribution;
- recovery-length distribution;
- probability of ruin under tested sizing;
- tail sensitivity.

Risk scaling is prohibited until this stage passes.

---

## 21. Risk Lab — After Raw Edge Only

Candidate risk levels:

- 0.25%;
- 0.50%;
- 0.75%;
- 1.00%.

Optional 1.25% research may be run only after lower-risk behavior is understood.

Prohibited:

- martingale;
- grid recovery;
- loss-recovery sizing;
- doubling after losses;
- hidden leverage escalation.

---

## 22. Promotion Gates

V3 is not called a successful Profit Hunter merely because it is better than losing V2.

### 22.1 Research Targets

Preferred targets:

- full-period PF ≥ 1.50;
- rolling walk-forward PF ≥ 1.25;
- stressed PF > 1.05;
- positive net expectancy;
- positive expectancy in R;
- max DD preferably <10–12%;
- profitable majority of outer walk-forward windows;
- materially improved PCR;
- stable parameters;
- no single year/session responsible for the entire edge.

These are promotion targets, not guaranteed outcomes.

### 22.2 Hard Rejection Conditions

Reject or return to research if:

- OOS PF <1.0;
- negative OOS expectancy;
- cost stress destroys edge under modest assumptions;
- material look-ahead / causality defect;
- unexplained dataset leakage;
- narrow parameter spike;
- profit depends primarily on compounding;
- broker-valid SL/TP cannot be maintained;
- native MT5 parity materially disagrees with research behavior.

---

## 23. Native MT5 Certification

Only after research promotion:

1. generate / update the MQL5 candidate;
2. compile in native MetaEditor;
3. require 0 errors;
4. warnings must be reviewed and resolved or explicitly accepted with rationale;
5. run PXBT XAUUSD using `Every tick based on real ticks` where available;
6. verify broker symbol specification;
7. verify SL/TP/fill semantics;
8. compare trade identities and metrics against research control expectations;
9. investigate parity mismatches before promotion.

No structural or Python-only test may be described as native compilation.

---

## 24. DEMO Forward Ladder

After MT5 certification:

```text
20 trades
   ↓
50 trades
   ↓
100 trades
   ↓
250 trades
   ↓
500 trades
```

At each gate compare:

- PF;
- expectancy;
- WR;
- spread;
- slippage;
- latency;
- MFE;
- MAE;
- PCR;
- DD;
- specialist mix;
- regime mix;
- research-vs-forward drift.

Fail closed on material execution or edge drift.

No automatic LIVE promotion.

---

## 25. Champion / Challenger Contract

- Existing V2.17 control remains immutable.
- HFS V2 remains a failed-alpha control for comparison.
- Every V3 experiment gets a unique immutable experiment ID.
- Candidate logic is never silently substituted into the control.
- Every promotion decision uses identical data and execution assumptions where comparison requires it.
- The V3 hybrid may include only specialists that individually justify inclusion or demonstrably improve the hybrid under ablation testing.

---

## 26. Implementation Deliverables

The implementation plan following approval of this specification SHALL produce, in order:

1. frozen benchmark manifests for V2.17 and HFS V2;
2. causal feature and event-ID contracts;
3. specialist research harness;
4. Alpha Tournament outputs;
5. failure-trade attribution report;
6. MFE/MAE and PCR lab;
7. Exit Tournament outputs;
8. rolling walk-forward report;
9. cost/robustness/placebo report;
10. Monte Carlo risk report;
11. selected V3 strategy specification;
12. single production-candidate `.mq5` source;
13. native compile evidence;
14. native MT5 real-tick certification report;
15. DEMO canary package only after certification.

---

## 27. Definition of Success

AUREON Ω V3 Profit Hunter succeeds only if the rebuilt strategy demonstrates a repeatable, causal, post-cost edge that survives walk-forward, stress, robustness, and native broker-realistic testing.

A large backtest balance alone is explicitly insufficient.

The desired operating behavior is:

> Detect real edge → wait for causal trigger → enter with validated protection → harvest efficiently → preserve exceptional runners → exit when edge decays → suppress stale re-entry → immediately search for the next independent opportunity.

---

## 28. Review Gate

This document defines architecture and research semantics only. It does **not** authorize implementation yet.

After user approval of this written specification, the next step is to create a detailed implementation plan with explicit files, tests, stages, and verification commands before writing V3 production code.
