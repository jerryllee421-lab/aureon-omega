# AUREON Ω — Super Scalper Control Architecture

**Date:** 2026-10-04  
**Status:** Approved design specification  
**Scope:** Research, evidence governance, DEMO execution, recovery, and certification for the AUREON Ω Gold automation stack  
**Primary market:** XAUUSD / Gold  
**Primary strategy family:** AUREON V7/V9.x exhaustion-liquidity / Super Scalper lineage  
**Execution boundary:** Research and DEMO only. LIVE execution is prohibited by this specification.

## 1. Purpose

AUREON Ω must evolve from a collection of strong research artifacts and broker-specific execution lanes into one governed trading system that:

1. preserves immutable controls and benchmark strategies;
2. learns only from reproducible evidence;
3. separates strategy decisions from broker execution;
4. fails closed when data, execution state, or account state is ambiguous;
5. can resume safely after interruption;
6. records enough lineage to explain why a candidate was promoted or rejected; and
7. supports final Strategy Tester / DEMO certification without allowing LIVE execution.

The system is not optimized for maximum backtest balance. It is optimized for sustainable, unseen, cost-adjusted expectancy and execution integrity.

## 2. Non-negotiable constraints

- XAUUSD / Gold remains the primary market.
- The frozen control logic must not be mutated in-place.
- Any new feature must prove incremental value against the control before promotion.
- All research features use completed bars only.
- Multi-timeframe data must be timestamp-safe and free of future-bar leakage.
- HOLDOUT data must not influence candidate selection.
- Every research artifact used for promotion must be cryptographically identifiable.
- Strategy logic must not be duplicated independently inside broker adapters.
- Broker adapters must consume a common immutable trade-intent contract.
- DEMO execution must fail closed on invalid account, symbol, data, spread, slippage, margin, state mismatch, duplicate intent, or reconciliation failure.
- LIVE order execution remains hard-blocked.
- Secrets must never be committed to Git or written to reports.
- No martingale, grid, or uncontrolled averaging-down behavior.
- One Gold position at a time remains the default certification policy.
- The default first DEMO canary remains deliberately conservative.

## 3. System architecture

The target architecture is:

```text
MARKET DATA
    |
    v
MARKET TRUTH
    |
    +--> Gold M1/M5/M15/H1/H4
    +--> optional DXY / yields / cross-market state
    |
    v
FEATURE ENGINE
    |
    +--> liquidity / sweep / reclaim
    +--> S/R / PDH / PDL / Asia range
    +--> volatility / regime
    +--> RSI / ADX / EMA displacement
    +--> MSS / BOS / displacement
    +--> FVG / retracement
    +--> Fib / trendline context
    |
    v
FORENSICS + SUPER SCALPER INTELLIGENCE
    |
    +--> event expectancy
    +--> portfolio expectancy
    +--> BLOCKED / WATCH / ARMED / TRIGGERED
    |
    v
GOVERNED EVIDENCE CONTRACT
    |
    +--> dataset hash
    +--> source commit
    +--> config hash
    +--> experiment/run identity
    +--> artifact hashes
    |
    v
EVOLUTION GOVERNOR
    |
    DEV -> VALIDATION -> candidate freeze -> HOLDOUT
    |
    +--> half-year stability
    +--> cost stress
    +--> parameter-neighborhood stability
    +--> walk-forward
    +--> native MT5 real ticks
    |
    v
FROZEN CANDIDATE
    |
    v
IMMUTABLE TRADE INTENT
    |
    v
RISK GOVERNOR
    |
    v
BROKER ADAPTER
    |
    +--> MT5 DEMO
    +--> cTrader DEMO
    +--> IG DEMO
    |
    v
ACK -> FILL -> MANAGE -> CLOSE -> RECONCILE
    |
    v
EVIDENCE LEDGER
```

## 4. Persistent project brain

A root-level `plan.md` becomes the authoritative operational resume point.

It must contain only high-level, non-secret state:

- current frozen control;
- current challenger;
- current research dataset and evidence identity;
- most recent compile/test verdict;
- most recent backtest/forward-test verdict;
- active broker lane and environment;
- current automation/scheduler state;
- unresolved incidents or blockers;
- last completed action;
- next action;
- links to detailed evidence and runbooks.

It must not contain API keys, passwords, refresh tokens, account secrets, or raw credentials.

Detailed reports remain in versioned research/evidence artifacts. `plan.md` links to them rather than duplicating them.

## 5. Market Truth layer

The Market Truth layer is responsible only for canonical, timestamped observations.

It must:

- normalize symbol names and broker-specific naming;
- normalize broker/server timestamps to the configured research clock;
- retain raw event times alongside normalized UTC;
- reject stale or missing data;
- expose only completed bars to strategy logic;
- distinguish real-tick, reconstructed, and proxy data;
- record source/provider identity;
- record spread and bid/ask context where available;
- reject silent forward filling across unavailable market periods;
- make data quality a first-class status.

Cross-market data such as DXY may be added only as a separate state input. It must not become a hard gate until ablation proves incremental value.

## 6. Feature Engine

The Feature Engine produces deterministic features and ordered event timestamps.

Required Gold feature families:

- liquidity sweep / reclaim;
- previous-day high / low;
- Asian-session high / low;
- confirmed swing support/resistance;
- volatility state;
- RSI exhaustion;
- ADX regime;
- EMA displacement / extension;
- M5 structure break;
- ordered M1 raid -> reclaim -> MSS -> displacement -> FVG -> retracement;
- algorithmic trendline interaction;
- Fibonacci location context.

Every feature must be reproducible from historical data without look-ahead.

A feature may be used in production only after its marginal contribution is measured against the frozen control.

## 7. Super Scalper Intelligence

The Super Scalper decision layer has four externally visible states:

- `BLOCKED`
- `WATCH`
- `ARMED`
- `TRIGGERED`

The readiness score is not a win probability.

### BLOCKED

Triggered by any hard veto including:

- no valid frozen context;
- stale market data;
- unsupported volatility regime;
- spread/slippage consumes the empirical edge;
- anchor/setup expiry;
- existing conflicting Gold exposure;
- daily-loss limit reached;
- drawdown limit reached;
- invalid account or symbol;
- invalid broker specification;
- insufficient margin;
- duplicate intent;
- unresolved reconciliation mismatch.

### WATCH

The frozen context is valid but the execution microstructure is incomplete.

### ARMED

The context is strong and most microstructure conditions are present, but the final trigger is not yet complete.

### TRIGGERED

The validated context, ordered microstructure sequence, cost gate, risk gate, and final trigger are all satisfied.

### Calibration

Initial engineering weights may be used only as provisional readiness weights.

Final weights must be calibrated from governed research evidence.

Calibration must answer questions such as:

- incremental value of M1 MSS;
- displacement-size threshold value;
- FVG/retest value;
- time-decay after the M5 anchor;
- session/location interaction;
- spread/slippage sensitivity;
- DXY confirmation or divergence value.

No score may be presented as a statistical confidence/probability until probability calibration has been demonstrated on untouched data.

## 8. Governed research evidence

All candidate promotion decisions must be based on a standard evidence contract.

The contract must include:

- schema version;
- strategy name/version;
- dataset SHA-256;
- source commit;
- configuration identity/hash;
- run ID;
- control metrics;
- challenger metrics;
- DEV metrics;
- VALIDATION metrics;
- HOLDOUT metrics;
- half-year metrics;
- cost-stress metrics;
- neighborhood-stability metrics;
- evidence-file SHA-256 manifest;
- verdict;
- reason codes.

Candidate selection must use VALIDATION only.

HOLDOUT is opened only after the candidate is frozen.

Required rejection reasons include:

- insufficient sample;
- negative expectancy;
- inadequate profit factor;
- excessive drawdown;
- OOS collapse;
- temporal instability;
- evidence lineage missing;
- holdout leakage risk;
- cost-stress failure;
- parameter fragility;
- native MT5 parity failure.

## 9. Promotion hierarchy

The canonical promotion ladder is:

```text
RESEARCH
  ->
ROBUSTNESS
  ->
NATIVE_MT5_REAL_TICK
  ->
PARITY
  ->
DEMO_CANARY
  ->
DEMO_FORWARD
  ->
CERTIFIED_DEMO
```

A candidate cannot skip a stage.

A historical backtest cannot authorize DEMO execution by itself.

A DEMO canary certifies execution integrity, not market edge.

A five-trade canary is sufficient only to evaluate execution plumbing, reconciliation, duplicate protection, stop/target handling, and evidence completeness.

## 10. Immutable TradeIntent contract

The strategy engine must emit one immutable `TradeIntent` object.

Minimum fields:

- intent_id;
- strategy_id;
- strategy_version;
- source_commit;
- evidence_run_id;
- symbol;
- direction;
- signal_time;
- trigger_time;
- reference_price;
- entry_type;
- entry_price/reference;
- stop_loss;
- tp1;
- tp2;
- tp3;
- invalidation;
- risk_fraction;
- readiness_state;
- readiness_score;
- feature/evidence references;
- expiry time;
- checksum/hash.

Once emitted, the intent cannot be silently mutated.

If broker constraints require an execution-side change, the adapter must create a separate execution-adjustment record rather than altering the original intent.

## 11. Risk Governor

The Risk Governor sits between TradeIntent and any broker adapter.

It must verify, at minimum:

- environment is DEMO;
- account is not LIVE;
- symbol resolves to Gold;
- symbol specification is fresh and valid;
- trade mode permits the requested action;
- market data is fresh;
- spread is within configured tolerance;
- expected slippage is within tolerance;
- volume is valid for broker min/max/step;
- stop distance is valid;
- stop loss exists;
- margin is sufficient;
- no conflicting Gold position exists;
- no conflicting pending Gold order exists;
- daily-loss limit is not breached;
- drawdown limit is not breached;
- canary trade limit is not breached;
- intent ID has not already been consumed;
- local/broker state is reconciled.

Any failed gate returns a deterministic rejection reason.

## 12. Broker adapters

MT5, cTrader, and IG must be treated as adapters, not strategy implementations.

Adapters are responsible for:

- symbol mapping;
- volume mapping;
- order-type translation;
- broker-specific fill policy;
- broker acknowledgements;
- execution timestamps;
- partial-close semantics;
- stop/target modification;
- error normalization;
- reconnect/recovery handling;
- broker-state reconciliation.

Adapters may not recalculate the Super Scalper signal or redefine strategy thresholds.

## 13. Execution lifecycle

The execution lifecycle is:

```text
TradeIntent
  ->
Risk Governor PASS
  ->
ExecutionRequest
  ->
Broker ACK
  ->
Fill
  ->
Position state
  ->
TP1 / TP2 partial management
  ->
TP3 runner / invalidation / stop
  ->
Close
  ->
Reconciliation
  ->
Evidence ledger
```

Every state transition must be auditable.

Unknown order outcomes are treated as unresolved incidents. The system must reconcile before retrying.

Duplicate-intent protection survives process restart.

## 14. Recovery and automation

Automation may:

- resume interrupted research;
- rerun failed non-order data jobs;
- regenerate evidence reports;
- reconcile known broker state;
- continue scheduled forward monitoring;
- repair idempotent local state;
- notify on meaningful incidents.

Automation may not:

- guess whether an ambiguous order filled;
- issue a replacement order until reconciliation resolves ambiguity;
- enable LIVE trading;
- bypass a failed risk gate;
- clear user/error pauses without a verified recovery condition.

Only one execution run may hold the trade lock at a time.

## 15. DEMO canary policy

The first Super Scalper execution certification remains conservative.

Default initial canary:

- DEMO only;
- one Gold position at a time;
- one trade/day initially;
- 0.25% risk per trade;
- 1.5% daily-loss halt;
- 3.0% drawdown halt;
- explicit execution arm required;
- automatic halt after configured canary count;
- zero unresolved reconciliation mismatches required.

Risk may increase only after a separate evidence-backed decision.

## 16. Supabase evidence model

Supabase becomes the persistent governed evidence store.

Existing research lineage entities must be populated instead of leaving MT5/Python artifacts detached.

Minimum persisted relationships:

```text
dataset
  -> experiment
      -> run
          -> candidate/test result
              -> artifact manifest
              -> promotion verdict
```

The production database must not be mutated from unreviewed local research code.

Repository migration history must be reconciled with production migration state.

RLS/service-only table intent must be explicit and documented.

## 17. GitHub and CI governance

All strategy/control-plane changes occur through branches and pull requests.

Required CI classes:

- Python/unit tests;
- evidence-contract tests;
- anti-holdout-leakage tests;
- execution-free research-tooling checks;
- MQL5 static checks;
- MetaEditor compile where available;
- immutable-control hash check;
- artifact hash manifest verification.

No candidate becomes the new frozen champion merely because a PR merged.

Promotion is a separate evidence-governance action.

## 18. Error handling

The default error policy is fail closed.

Examples:

- missing/stale market data -> BLOCKED;
- account environment mismatch -> execution prohibited;
- unknown symbol mapping -> execution prohibited;
- invalid volume -> execution prohibited;
- no stop loss -> execution prohibited;
- spread/slippage breach -> execution prohibited;
- insufficient margin -> execution prohibited;
- duplicate intent -> execution prohibited;
- broker/API timeout after order submission -> unresolved incident, reconcile before retry;
- state mismatch -> execution prohibited;
- research schema/hash failure -> candidate cannot be promoted.

Every failure must have a stable machine-readable reason code plus human-readable context.

## 19. Testing strategy

### Unit

Test deterministic feature math, clock normalization, readiness-state transitions, risk gates, intent hashing, volume normalization, and broker-error normalization.

### Research

Verify:

- no look-ahead;
- DEV/VALIDATION/HOLDOUT chronology;
- validation-only selection;
- event-vs-portfolio expectancy;
- half-year stability;
- cost stress;
- parameter-neighborhood stability;
- walk-forward behavior.

### MT5

Require:

- 0 compile errors;
- 0 compile warnings for promoted builds;
- real-tick compatibility;
- deterministic closed-bar behavior;
- expected evidence CSV output;
- no LIVE-order path in research builds.

### DEMO

Verify:

- account/environment enforcement;
- one-position policy;
- duplicate protection;
- OrderCheck/preflight;
- broker ACK/fill capture;
- SL/TP behavior;
- partial management;
- restart recovery;
- reconciliation;
- automatic canary halt;
- complete evidence record.

## 20. Success criteria

This architecture is successfully implemented when:

- root `plan.md` exists and accurately resumes project state;
- research evidence is persisted with hashes and lineage;
- V9.x research artifacts can be ingested into the canonical evidence contract;
- HOLDOUT cannot influence selection;
- the Super Scalper state machine is calibrated from evidence;
- one immutable TradeIntent contract is used across broker adapters;
- broker adapters contain no independent strategy interpretation;
- Risk Governor can veto every unsafe execution condition deterministically;
- restart/duplicate/reconciliation safety is tested;
- MT5/cTrader/IG DEMO adapters can be evaluated against the same intent;
- canary evidence is complete;
- LIVE execution remains impossible.

## 21. Explicitly out of scope

- LIVE-money enablement;
- guaranteed profitability;
- martingale or grid behavior;
- autonomous parameter mutation directly in production;
- opaque LLM direction prediction as the primary signal;
- broker-specific strategy forks;
- adding every available cross-market feature simultaneously;
- using HOLDOUT to choose parameters;
- treating a high readiness score as a win probability.

## 22. Implementation order

The architecture is implemented in this order:

1. persistent `plan.md` and project resume contract;
2. evidence contract and ingestion;
3. Super Scalper calibration/evidence interfaces;
4. immutable TradeIntent contract;
5. shared Risk Governor;
6. broker-adapter conformance;
7. reconciliation/recovery;
8. CI and certification gates;
9. native MT5 real-tick validation;
10. one-trade DEMO canary;
11. five-trade DEMO canary;
12. forward DEMO certification.

No later phase may silently weaken an earlier safety or evidence requirement.
