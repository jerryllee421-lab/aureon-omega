# AUREON Ω V7.1 — Robustness & Execution Truth

V7.1 strengthens the Quantum Edge Lab by making **robustness, execution realism and selection-bias control** mandatory evidence layers.

## What changed

### 1. Authoritative research-run concurrency
Only the newest comprehensive DOE request on the branch is authoritative. New research requests cancel stale in-progress DOE runs so artifacts from superseded experiments cannot be mixed.

### 2. Broker Symbol Truth
A non-trading PrimeXBT probe now:
- starts on a safe chart rather than assuming a Gold symbol;
- enumerates broker symbols;
- discovers XAU/GOLD candidates;
- selects the strongest tradable match;
- fingerprints digits, point, tick size/value, contract size, volume rules, trade/calc mode, stops/freeze levels, fill/order/expiration modes, current spread and history coverage;
- places **zero orders** and keeps live trading disabled.

The full broker-native strategy workflow consumes the discovered symbol instead of hard-coding `XAUUSD.ecn`.

### 3. Immutable R basis + MAE/MFE
Campaign R-multiples are now measured from the **first actual fill and initial stop**.

Trailing the stop or adding campaign tranches must not artificially increase measured R.

Each campaign ledger records:
- first entry;
- initial stop;
- initial risk distance;
- maximum favorable excursion in R;
- maximum adverse excursion in R;
- holding time;
- deal exit reason;
- final excursion snapshot.

### 4. Pending-entry hardening
- unfilled pending orders no longer consume the daily traded-campaign count;
- daily campaign count increments on the first actual fill;
- pending orders reset immediately after expiry/session/invalidation;
- if broker-side `ORDER_TIME_SPECIFIED` is unsupported, ASTRA falls back to GTC while retaining deterministic EA-managed expiry;
- the custom XAU research symbol explicitly permits limit orders.

### 5. Rolling temporal robustness
Top fixed candidates are retested across four sequential windows:

1. 2025-08-20 → 2025-11-20
2. 2025-11-20 → 2026-02-20
3. 2026-02-20 → 2026-05-20
4. 2026-05-20 → 2026-08-20

This is a **temporal stability test**, not a replacement for untouched OOS.

The current gate requires at least:
- 4 evaluated windows;
- 3 positive windows;
- 20 combined trades;
- positive median expectancy;
- median PF ≥ 1.0;
- worst window DD ≤ 12%.

### 6. Deterministic spread degradation
OOS candidates are retested at:

- 1.00× baseline spread
- 1.25× spread
- 1.50× spread
- 2.00× spread

Promotion requires survival through **1.50×**.  
2.00× is retained as a tail diagnostic.

### 7. IID + moving-block Monte Carlo
The existing 5,000-path bootstrap remains, and V7.1 adds a **3-P/L-day moving-block bootstrap** to preserve short serial dependence and losing/winning streak structure better than IID reshuffling alone.

### 8. Multiple-testing diagnostic
Because ASTRA screens many timeframes, EMAs and parameter combinations, V7.1 adds a conservative one-sided daily-P/L test with Bonferroni adjustment using the number of screened hypotheses.

This is intentionally conservative and is not treated as proof of future profitability.

### 9. V7.1 Edge Registry
`ROBUST_OOS_CANDIDATE` now requires all of the following:

- existing conservative IS/OOS selection gate;
- OOS trades ≥ 20;
- OOS PF ≥ 1.10;
- positive OOS expectancy and net result;
- OOS DD ≤ 8%;
- IID Monte Carlo pass;
- moving-block Monte Carlo pass;
- rolling temporal pass;
- spread-stress pass;
- multiple-testing diagnostic support.

Only then can a strategy proceed to broker-native real-tick confirmation.

## Promotion chain

```
DATA TRUTH
→ REGIME
→ DOE
→ PARAMETER STABILITY
→ CROSS-FAMILY TEST
→ UNTOUCHED OOS
→ ROLLING TEMPORAL VALIDATION
→ MAE/MFE EXCURSION ANALYSIS
→ SPREAD DEGRADATION
→ IID + BLOCK MONTE CARLO
→ MULTIPLE-TESTING DIAGNOSTIC
→ EDGE REGISTRY
→ BROKER-NATIVE CONFIRMATION
→ DEMO SHADOW / FORWARD VALIDATION
```

## Non-negotiable controls

- No fabricated market data.
- No live-money execution in the research pipeline.
- No strategy promotion from in-sample ranking alone.
- No AI override of deterministic signal/risk gates.
- No promotion if the robustness evidence is incomplete.
- Broker-native symbol/execution truth is mandatory before forward promotion.
