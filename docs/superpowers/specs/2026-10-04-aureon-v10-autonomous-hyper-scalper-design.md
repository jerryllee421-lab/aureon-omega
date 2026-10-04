# AUREON Ω V10 — Autonomous Hyper Scalper Intelligence

**Date:** 2026-10-04  
**Status:** Design specification for implementation  
**Branch:** `feature/v10-hyper-scalper-intelligence`  
**Primary market:** XAUUSD / Gold  
**Artifact target:** One self-contained MQL5 Expert Advisor file  
**External parameter setup:** None required  
**External .set file:** Not required  
**External indicators/libraries:** None beyond the standard MQL5 runtime  
**Execution policy:** Strategy Tester and DEMO execution supported automatically; REAL-account orders remain hard-blocked until a separate live certification gate is completed.

## 1. Objective

Build one production-grade, self-contained Gold scalping EA that:

- requires no manual input configuration;
- contains all strategy, risk, session, execution, and intelligence parameters internally;
- automatically identifies Gold symbol characteristics and broker constraints;
- performs multi-timeframe market analysis;
- runs an event-driven microstructure engine rather than waiting only for M5 bars;
- evaluates at least 1,000 shadow/micro opportunities on an active Gold trading day when sufficient market activity exists;
- never forces a minimum number of real orders;
- executes only opportunities whose estimated net expectancy remains positive after estimated transaction costs;
- manages entries, stops, targets, partial exits, break-even, trailing, adverse exits, time exits, and recovery autonomously;
- records enough evidence to diagnose whether each intelligence layer adds value.

The optimization target is **net expectancy and execution quality**, not raw trade count.

## 2. Non-negotiable frequency rule

AUREON V10 SHALL NOT contain a rule that forces a minimum number of executed trades.

Instead:

1. The microstructure engine shall be capable of evaluating 1,000+ independent shadow opportunities per active trading day when tick activity permits.
2. The execution engine may technically support up to 1,000 entries/day.
3. A real/DEMO order may be created only when the Edge Governor and Risk Governor both pass.
4. No frequency target may override a spread, slippage, drawdown, daily-loss, duplicate-intent, margin, or data-quality veto.
5. If only 40 qualified trades exist, the EA executes at most 40. If 400 qualify, it may execute up to 400 subject to exposure and risk limits.

## 3. Single-file autonomous configuration

The EA must not expose a large manual `input` surface.

All configuration lives in the source file through:

- internal constants;
- strongly typed configuration structs;
- broker-derived runtime values;
- market-derived adaptive values;
- account/environment-derived risk values.

The EA shall initialize itself by:

1. detecting whether it is in Strategy Tester, DEMO, or REAL;
2. resolving the Gold symbol from the attached chart;
3. reading digits, point, tick size, tick value, volume min/max/step, stops level, freeze level, margin mode, and supported filling modes;
4. measuring current spread and tick cadence;
5. deriving server-to-UTC offset from runtime observations/configured deterministic rules;
6. loading the internal `V10_AUTONOMOUS` strategy profile;
7. enabling execution automatically in Strategy Tester and DEMO;
8. forcing monitor/shadow-only mode on REAL accounts.

There is no required `.set` file.

## 4. Runtime architecture

```text
BROKER TICKS
   |
   +--> Tick Quality / Spread / Latency
   |
   +--> 5s Micro Bars
   +--> 15s Micro Bars
   +--> 30s Micro Bars
   +--> M1
   +--> M5
   +--> M15
   +--> H1
   |
   v
MARKET STATE ENGINE
   |
   +--> EMA21 / EMA55 / EMA100 / EMA200
   +--> VWAP / AVWAP / σ bands
   +--> POC / VAH / VAL / HVN / LVN
   +--> Liquidity / sweep / reclaim
   +--> MSS / BOS / displacement
   +--> FVG / retracement
   +--> S/R / PDH / PDL / Asia range
   +--> ATR / volatility / spread state
   |
   v
STRATEGY PORTFOLIO
   |
   +--> Trend Pullback
   +--> Liquidity Reversal
   +--> Expansion Breakout
   +--> FVG Recycler
   |
   v
EDGE GOVERNOR
   |
   v
STOP + TARGET INTELLIGENCE
   |
   v
RISK GOVERNOR
   |
   v
TRADE INTENT
   |
   v
MT5 EXECUTION
   |
   v
POSITION MANAGER
   |
   v
EVIDENCE + ADAPTIVE DEGRADATION STATE
```

## 5. Timeframe roles

### H1
Used for macro regime:

- EMA100 direction and slope;
- EMA55/100/200 ordering;
- price relative to EMA100 and EMA200;
- broad volatility state;
- major swing structure.

### M5
Used for intraday location and setup context:

- EMA100 dynamic S/R;
- EMA21/55/100/200 structure;
- session VWAP;
- AVWAP;
- POC / VAH / VAL;
- liquidity sweep/reclaim;
- S/R, PDH/PDL, Asian range;
- setup anchor creation.

### M1
Used for precision execution:

- EMA21 pullback/reclaim;
- M1 MSS/BOS;
- displacement;
- FVG;
- micro liquidity;
- execution-quality confirmation.

### 5s / 15s / 30s internal bars
Used for hyper-scalper timing:

- micro MSS;
- micro displacement;
- wick rejection;
- micro FVG;
- spread expansion;
- micro momentum decay;
- adverse exit;
- re-entry timing.

## 6. EMA intelligence

EMA100 becomes a first-class regime/location feature.

The EA shall maintain:

- EMA21;
- EMA55;
- EMA100;
- EMA200;

on M1, M5, M15, and H1 where required.

EMA100 states include:

- STRONG_BULL;
- BULL_PULLBACK;
- EMA100_RECLAIM;
- EMA100_SUPPORT;
- COMPRESSION;
- NEUTRAL;
- EMA100_RESISTANCE;
- EMA100_REJECTION;
- BEAR_PULLBACK;
- STRONG_BEAR;
- EXTENDED_ABOVE;
- EXTENDED_BELOW.

Derived features include:

- price-to-EMA100 distance in ATR;
- EMA100 slope normalized by ATR;
- EMA21-to-EMA100 separation;
- EMA55/100/200 stack;
- EMA21/100 compression;
- EMA100/200 compression;
- reclaim/rejection age;
- cross/retest count;
- distance-to-EMA100 versus VWAP/POC cluster.

EMA100 is not a universal hard gate. Its state contributes to strategy-specific expected edge.

## 7. VWAP / volume-profile intelligence

The EA shall calculate internally:

- daily VWAP;
- London VWAP;
- New York VWAP;
- anchored VWAP from setup anchor;
- VWAP ±1σ and ±2σ;
- POC;
- VAH;
- VAL;
- approximate HVN/LVN;
- POC migration;
- value-area reclaim/rejection;
- real-volume fraction.

Volume source order:

1. broker real volume when valid;
2. broker tick volume otherwise.

The evidence log must identify which source was used.

## 8. Strategy portfolio

### 8.1 Trend Pullback Engine

Long example:

- H1 EMA100 rising;
- M5 EMA100 rising;
- price above EMA100;
- EMA21/55/100 structure supportive;
- pullback toward EMA21, EMA100, VWAP, AVWAP, POC, or value boundary;
- liquidity sweep or rejection;
- M1 EMA21 reclaim;
- M1 MSS;
- displacement;
- optional FVG retracement;
- positive net edge.

Short is mirrored.

### 8.2 Liquidity Reversal Engine

Long example:

- low sweeps recent liquidity;
- exhaustion/extension state;
- VAL / VWAP lower band / EMA100 support cluster;
- reclaim;
- M1/micro MSS;
- displacement;
- spread and cost acceptable.

Designed for the historical V7 exhaustion-liquidity family.

### 8.3 Expansion Breakout Engine

Requires:

- EMA21/EMA100 or EMA55/EMA100 compression;
- volatility compression;
- liquidity build-up;
- clean displacement;
- breakout/retest;
- supportive volume migration;
- acceptable spread.

### 8.4 FVG Recycler Engine

Tracks multiple valid FVGs simultaneously.

A zone may be traded more than once only if:

- the zone remains valid;
- a fresh micro trigger occurs;
- duplicate-intent rules pass;
- cost-adjusted expected edge remains positive;
- engine degradation state is not blocked.

Repeated entries are evidence-driven, not automatic.

## 9. Edge Governor

The Edge Governor estimates whether the next trade is worth paying for.

It combines:

- strategy family;
- direction;
- session;
- volatility bucket;
- EMA100 state;
- distance from EMA100;
- VWAP state;
- POC/value-area state;
- liquidity context;
- M1 trigger quality;
- microstructure quality;
- spread;
- expected slippage;
- setup age;
- recent engine performance.

The runtime score is not advertised as a probability.

The execution decision is:

```text
estimated_gross_edge_R
- estimated_spread_cost_R
- estimated_slippage_cost_R
- commission_cost_R
= estimated_net_edge_R
```

Trade only when estimated net edge exceeds the internal floor.

## 10. Shadow-learning lane

Every qualifying micro event may create a shadow trade even when no broker trade is placed.

Shadow trades record:

- strategy engine;
- direction;
- timestamp;
- entry reference;
- stop candidate;
- target candidates;
- EMA state;
- VWAP/POC state;
- volatility state;
- spread;
- MFE;
- MAE;
- result at 30s / 60s / 90s / 3m / 5m / 10m;
- hypothetical net R after costs.

The shadow lane is the mechanism used to reach high daily sample counts.

Shadow trades never alter account state.

## 11. Entry intelligence

A broker order requires all of:

1. valid market data;
2. valid strategy-engine setup;
3. fresh final trigger;
4. no duplicate intent;
5. execution cost below threshold;
6. positive estimated net R;
7. Risk Governor pass;
8. broker preflight pass.

The final trigger may occur on tick, 5s, 15s, 30s, or M1 state change.

The EA must not wait for a new M5 bar once a valid setup anchor exists.

## 12. Stop-loss intelligence

The EA evaluates multiple stop candidates:

- sweep extreme;
- micro swing invalidation;
- M1 swing invalidation;
- FVG invalidation;
- EMA100 structural invalidation;
- VWAP/value-area invalidation;
- ATR floor;
- broker minimum stop distance.

The selected stop must:

- invalidate the setup logically;
- satisfy broker stop constraints;
- include spread/micro-volatility buffer;
- remain within the maximum permitted risk budget;
- leave sufficient expected upside.

A trade is rejected if no valid stop provides positive expected utility.

## 13. Profit-target intelligence

Candidate targets include:

- EMA21;
- EMA100;
- VWAP;
- AVWAP;
- POC;
- VAH;
- VAL;
- PDH/PDL;
- Asian high/low;
- micro/internal liquidity;
- external liquidity;
- FVG boundaries;
- R-multiple anchors.

Target selection uses both market structure and historical MFE behavior.

### MICRO profile

For very short-duration trades:

- one primary target;
- optional runner;
- minimal partial-close overhead.

### SNIPER profile

For larger setup quality:

- TP1 internal liquidity / VWAP;
- TP2 POC / value boundary;
- TP3 external liquidity / session extreme;
- optional runner if trend remains favorable.

## 14. Exit intelligence

A position may exit because of:

- hard SL;
- TP;
- opposing micro MSS;
- EMA21 reclaim failure;
- EMA100 invalidation;
- VWAP rejection flip;
- adverse POC/value migration;
- spread explosion;
- micro volatility shock;
- momentum collapse;
- time stop;
- daily risk governor;
- equity drawdown governor;
- emergency broker-state mismatch.

Time-stop candidates to be internally evaluated include:

- 30 seconds;
- 60 seconds;
- 90 seconds;
- 3 minutes;
- 5 minutes;
- 10 minutes.

## 15. Position management

The EA manages:

- break-even;
- profit lock;
- ATR/microstructure trailing;
- structural trailing;
- partial closes when efficient;
- runner management;
- maximum holding time;
- restart recovery.

Position management is event-driven and runs every tick.

## 16. Risk architecture for high frequency

Per-trade risk must be much smaller than low-frequency V9.x defaults.

The internal risk engine shall derive a risk fraction from:

- account equity;
- broker minimum lot;
- stop distance;
- session loss budget;
- rolling 5-minute loss budget;
- rolling hourly loss budget;
- daily loss budget;
- recent strategy-engine degradation;
- current spread/slippage regime.

Hard governors include:

- maximum per-trade risk;
- rolling 5-minute loss;
- rolling hourly loss;
- daily loss;
- equity drawdown;
- consecutive loss limit;
- spread circuit breaker;
- rejection-rate circuit breaker;
- latency/tick-staleness circuit breaker;
- strategy-engine kill switch;
- account/broker-state mismatch.

Risk cannot be increased merely to meet a trade-frequency target.

## 17. Exposure model

V10 may support more than one logical strategy intent, but broker exposure remains bounded.

Default certification behavior:

- net aggregate Gold exposure cap;
- maximum simultaneous positions determined from account mode and risk budget;
- no uncontrolled pyramiding;
- no martingale;
- no grid;
- no averaging down after invalidation.

For netting accounts, the EA must maintain an internal intent ledger so multiple strategy decisions are not confused with one broker position.

## 18. Trade-intent identity

Each order candidate receives a deterministic intent identity from:

- strategy engine;
- direction;
- setup anchor;
- trigger timestamp;
- symbol;
- source-state checksum.

An intent cannot be submitted twice unless a defined re-entry event creates a new intent.

Restart must not erase consumed-intent history for active/recent setups.

## 19. Autonomous session behavior

The EA internally recognizes:

- Asia;
- London;
- London/New York overlap;
- New York;
- low-liquidity/off-session state.

Each strategy engine may have different session expectancy.

No user session input is required.

DST handling is deterministic and internal.

## 20. Automatic engine degradation

Each strategy family maintains rolling forward statistics.

Possible states:

- ENABLED;
- DEGRADED;
- SHADOW_ONLY;
- BLOCKED.

An engine can move to SHADOW_ONLY or BLOCKED if:

- recent net expectancy turns materially negative;
- spread-adjusted performance collapses;
- execution rejection rises;
- slippage exceeds limits;
- data quality degrades.

Automatic re-enable requires sufficient new shadow evidence, not a single winning trade.

## 21. Execution environment policy

### Strategy Tester

Broker orders allowed inside tester.

### DEMO

Execution automatically enabled after environment and broker preflight passes.

### REAL

The EA runs full analysis, shadow trades, dashboard, and evidence collection, but **broker order submission is hard-blocked in code**.

REAL enablement requires a separate certification version after:

- native real-tick validation;
- DEMO canary;
- forward DEMO evidence;
- broker-specific execution certification;
- explicit live-risk specification.

## 22. Performance engineering

Because the EA is tick-driven:

- slow indicators recalculate only on their timeframe's new closed bar;
- VWAP/volume state updates incrementally;
- micro-bars are aggregated from ticks in fixed-size in-memory structures;
- no full-history scans occur on every tick;
- volume profiles use bounded rolling/session arrays;
- chart objects are minimized;
- telemetry writing is buffered/batched where practical;
- heavy research-only calculations are disabled from the hot execution path.

## 23. Evidence outputs

Although no external configuration is required, the EA may write evidence CSV files.

Required records:

- shadow opportunities;
- executed intents;
- order preflight;
- fills;
- exits;
- MFE/MAE;
- engine state;
- risk governor state;
- EMA100 state;
- VWAP/POC state;
- microstructure state;
- execution costs;
- rejection reason.

The EA itself remains one MQ5 file.

## 24. Dashboard

The on-chart dashboard must show at minimum:

- AUREON V10 state;
- environment: TESTER / DEMO / REAL-MONITOR;
- active strategy engine;
- H1/M5 EMA100 regime;
- M1 EMA21 trigger state;
- VWAP/AVWAP;
- POC/VAH/VAL;
- spread;
- net-edge estimate;
- risk budget;
- open exposure;
- trades today;
- shadow opportunities today;
- daily P/L;
- current governor state;
- blocked reason when applicable.

No manual dashboard controls are required for core operation.

## 25. Internal configuration profile

All numeric defaults are compiled into an internal `V10Config` structure.

The initial profile shall preserve known AUREON evidence where appropriate:

- V7/V9 exhaustion context remains available as one engine;
- RSI14;
- ADX14;
- ATR14;
- 20-bar liquidity sweep;
- 2.0 ATR exhaustion extension;
- normalized volatility regime;
- EMA21 precision trigger;
- EMA100 regime/location;
- EMA55/200 contextual structure;
- VWAP/POC intelligence;
- spread/slippage hard gates.

High-frequency-specific risk and timing values are treated as certification parameters and must be validated in tester/DEMO before any future REAL version.

## 26. Testing requirements

### Compile

- 0 MetaEditor errors;
- 0 MetaEditor warnings.

### Determinism

- identical tick input produces identical decisions.

### Real-tick testing

- XAUUSD;
- Every tick based on real ticks;
- no optimization during first parity run.

### Functional tests

Verify:

- micro-bar aggregation;
- EMA100 state transitions;
- VWAP/POC calculations;
- intent de-duplication;
- cost gate;
- stop selection;
- target selection;
- time stops;
- adverse exits;
- restart recovery;
- netting/hedging account handling;
- daily/rolling risk governors;
- engine degradation.

### Research comparison

Compare:

- V7/V9.x control;
- V10 Trend Pullback;
- V10 Liquidity Reversal;
- V10 Expansion Breakout;
- V10 FVG Recycler;
- combined V10 portfolio.

Metrics:

- trade count;
- shadow count;
- expectancy;
- PF;
- drawdown;
- MFE/MAE;
- average holding time;
- spread/slippage cost;
- half-year stability;
- session performance;
- long/short asymmetry;
- parameter-neighborhood stability.

## 27. Delivery artifact

The user-facing delivery is:

`AUREON_OMEGA_V10_AUTONOMOUS_HYPER_SCALPER.mq5`

It must contain everything required to operate.

There is no required:

- `.set` file;
- manual parameter entry;
- external indicator;
- Python runtime;
- DLL;
- network API;
- external AI API;
- VPS-specific dependency.

## 28. Success criteria

V10 is implementation-complete only when:

- the single MQ5 file compiles with 0 errors and 0 warnings;
- it attaches without parameter initialization errors;
- it self-configures on a Gold chart;
- Strategy Tester execution works on native MT5;
- DEMO execution works without external parameter setup;
- REAL execution remains impossible;
- the microstructure engine processes tick events correctly;
- 1,000+ daily shadow opportunities are achievable on sufficiently active sessions without forcing broker orders;
- all strategy families can be independently attributed;
- stops and targets are structure-aware;
- edge and risk governors can veto trades;
- restart/duplicate/reconciliation safety is verified;
- evidence outputs are complete enough to compare V10 against the frozen controls.

## 29. Explicitly prohibited behavior

- forcing trades to reach 1,000/day;
- martingale;
- grid recovery;
- averaging down after invalidation;
- deleting or bypassing stops to increase fill count;
- overriding daily/drawdown governors;
- hidden live-account execution;
- using future bars;
- treating EMA100 as a magical universal filter;
- claiming readiness score is a win probability;
- claiming profitability from backtest frequency alone.
