# AUREON Ω V7 — QUANTUM EDGE LAB

## Purpose

V7 separates **research discovery**, **signal qualification**, and **execution validation**.  
A parameter set is never promoted because it produced the highest historical balance.

The research objective is to identify repeatable XAUUSD behavior that survives:
- different timeframes and market regimes;
- nearby parameter values;
- untouched out-of-sample data;
- execution-cost degradation;
- Monte Carlo path reshuffling;
- broker-native MT5 confirmation;
- forward demo observation.

Real-money execution is outside this research pipeline.

## Architecture

```
DATA TRUTH
  ↓
REGIME ENGINE
  ↓
STRATEGY FACTORY
  ↓
DOE / PARAMETER SCREENS
  ↓
PARAMETER STABILITY
  ↓
CROSS-FAMILY TESTS
  ↓
UNTOUCHED OOS
  ↓
MONTE CARLO / EXECUTION STRESS
  ↓
EDGE REGISTRY
  ↓
BROKER-NATIVE REAL-TICK CONFIRMATION
  ↓
DEMO FORWARD SHADOW EXECUTION
```

## Evidence layers

### 1. Data Truth
Pinned external bid/ask history is valid for broad OHLC research.  
True broker tick volume, symbol specification, live spread distribution and fill behavior must come from the target MT5 broker before forward promotion.

### 2. Regime Engine
Closed-bar deterministic labels:
- TREND_UP
- TREND_DOWN
- RANGE
- COMPRESSION
- EXPANSION_UP
- EXPANSION_DOWN
- HIGH_VOL_TRANSITION
- TRANSITION

Regime labels are explanatory context, not a forecast.

### 3. Strategy Factory
Independent strategy families remain separately attributable:
- liquidity sweep/reclaim reversal;
- trend pullback continuation;
- expansion breakout/retest;
- London liquidity raid;
- New York continuation/reversal.

No blended performance claim is permitted unless the portfolio logic itself is tested.

### 4. DOE
The current DOE screens:
- all native MT5 timeframes;
- dense EMA surfaces;
- HTF context and ADX;
- liquidity/sweep/reclaim geometry;
- MSS/displacement/FVG geometry;
- market versus pending execution;
- stop/TP/protection/trailing geometry;
- session/spread/deviation;
- position sizing and account risk constraints.

### 5. Stability
Prefer a broad parameter plateau over an isolated optimum.  
A candidate with excellent metrics at one exact parameter value but poor nearby values is considered fragile.

### 6. Setup Funnel
Each campaign must be traceable through:
```
SWEEP_RECLAIMED
→ WAITING_MSS
→ ENTRY_ZONE_ACTIVE
→ PENDING_ENTRY or MARKET_ENTRY
→ BUILDING
→ PROTECTED
→ PARTIAL_EXIT
→ RUNNER
→ COMPLETED
```
Invalidation, expiry, risk rejection and order rejection remain explicit terminal evidence.

### 7. OOS gate
A top in-sample configuration cannot become a candidate without untouched OOS evidence.

Minimum research gate:
- adequate independent trade sample;
- positive OOS net result and expectancy;
- PF greater than 1;
- controlled drawdown;
- meaningful retention of in-sample behavior.

### 8. Monte Carlo gate
Daily P/L blocks are bootstrap-resampled to stress sequence dependence.  
The registry records ending-balance and drawdown distributions rather than one historical path.

### 9. Edge Registry
Statuses:
- REJECT
- RESEARCH
- ROBUST_OOS_CANDIDATE
- BROKER_NATIVE_VERIFIED
- DEMO_FORWARD_VALIDATED

No status implies guaranteed future profitability.

### 10. Broker-native confirmation
Only robust OOS candidates proceed. Confirmation requires:
- actual target symbol metadata;
- broker-native historical ticks where available;
- broker spread/stops/freeze levels;
- pending-order capability;
- fill-policy compatibility;
- strategy results with realistic execution costs.

### 11. Demo forward
The final research stage compares:
- ASTRA theoretical entry;
- requested broker order;
- actual broker fill;
- slippage;
- spread;
- stop/TP compliance;
- partial-close behavior;
- realized versus planned R.

Live trading remains disabled until explicitly designed, reviewed and separately authorized.

## Promotion principle

The target is not the highest backtest return.

The target is a **persistent edge plateau** with:
1. positive expectancy,
2. adequate sample size,
3. bounded drawdown,
4. parameter stability,
5. OOS survival,
6. execution-stress resilience,
7. broker-native confirmation,
8. forward-demo consistency.
