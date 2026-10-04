# AUREON V10 Autonomous Hyper Scalper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver one self-contained MT5 EA file that requires no manual parameter setup and implements the approved V10 Gold Hyper Scalper architecture for Strategy Tester and DEMO testing.

**Architecture:** Extend the V9.5 single-file engine rather than rewrite the execution plumbing. Convert the external input surface into internal autonomous constants, add EMA100 regime intelligence and event-driven microstructure/shadow sampling, then preserve the existing VWAP/POC, risk-governor, evidence, virtual-control, and broker-order layers. REAL-account order submission remains hard-blocked.

**Tech Stack:** MQL5 / MetaTrader 5 standard library only.

**Spec:** docs/superpowers/specs/2026-10-04-aureon-v10-autonomous-hyper-scalper-design.md

## Global Constraints

- One MQ5 file.
- No required .set file or manual inputs.
- No DLL, Python, external indicator, or network API dependency.
- Strategy Tester and DEMO may execute automatically after preflight.
- REAL accounts remain analysis/shadow-only.
- Do not force 1,000 real orders/day; target 1,000+ shadow micro-opportunities when tick activity permits.
- No martingale, grid, averaging-down, or stop removal.

## Review Focus

- DEMO vs REAL environment resolution cannot accidentally enable REAL orders.
- Broker symbol/volume/stop/filling constraints must be respected.
- Micro-event sampling must not create duplicate broker intents.
- EMA100/VWAP/POC calculations must use closed-bar or current-tick data without future leakage.
- High-frequency risk limits must remain active even if the opportunity counter is high.

### Task 1: Autonomous configuration conversion
- Replace all MQL5 `input` declarations with source-internal configuration values.
- Update identifiers, version strings, evidence filenames, and automatic DEMO execution mode.
- Verify zero remaining `input` declarations and REAL hard block remains.

### Task 2: EMA100 regime intelligence
- Add M1/M5/H1 EMA100 handles and state evaluation.
- Add EMA100 state, slope/distance, EMA21/100 compression and stack information to decision scoring/dashboard/evidence.
- Verify handles release on deinit and state uses no future bars.

### Task 3: Event-driven micro opportunity engine
- Add 5s/15s/30s tick-aggregated micro bars.
- Generate deduplicated shadow opportunities from EMA21 reclaim, micro break/displacement, FVG and liquidity/VWAP/POC interactions.
- Track daily shadow count and keep broker orders gated by the existing production decision path.

### Task 4: High-frequency autonomous risk/exits
- Internalize higher execution capacity while retaining loss/drawdown/cost/duplicate gates.
- Add rolling loss/consecutive-loss/engine-state controls where feasible without changing broker safety semantics.
- Keep dynamic structural TP/SL behavior and event-driven position management.

### Task 5: Verification and delivery
- Run static source contract checks, delimiter/brace checks, unresolved identifier scan, forbidden LIVE-order-path scan, and package checksum.
- Attempt native MetaEditor/Wine compile if available; otherwise state that authoritative compile remains the user's MT5 gate.
- Deliver AUREON_OMEGA_V10_AUTONOMOUS_HYPER_SCALPER.mq5.
