# AUREON Ω PRIME — cTrader Cloud Executor

## Purpose
A parallel, demo-first execution lane for AUREON Ω PRIME using native cTrader Cloud cBots. This removes the PC/VPS dependency while preserving the external Gold research factory and immutable V2.12 control.

## Architecture
Research/Evolution -> verified strategy manifest -> native cBot -> deterministic Risk Governor -> cTrader Cloud -> DEMO account -> reconciliation/evidence.

## Non-negotiable gates
- XAUUSD only for the Gold executor.
- DEMO only until forward certification is complete. `OnStart()` hard-stops whenever `Account.IsLive` is true.
- No AI call is required to place/manage a trade.
- No HTTP/WebSocket dependency in the execution-critical loop.
- Risk Governor cannot be bypassed by strategy logic.
- Every order must have an explicit stop loss.
- Stale/invalid market state, excessive spread, loss/drawdown limits, margin failure, or execution inconsistency veto entry.
- The historical V2.12 R943K result is a control benchmark, not a live-performance claim.
- Do not alter the frozen control parameters to make a cTrader result look similar.

## Parity-first implementation
The first cBot must reproduce the report-matched V2.12 behavior as faithfully as cTrader semantics allow. Differences in symbol specification, tick size, volume units, spread, commissions, fill model, timestamps and bar construction must be recorded as parity differences rather than hidden.

## Certification
1. Compile/static validation.
2. Native cTrader historical backtest.
3. Compare trade count/direction/entry timing and risk behavior with control.
4. Cost/slippage/spread stress.
5. One minimum-risk DEMO canary.
6. Verify order -> acknowledgement -> fill -> position -> SL/TP -> close -> reconciliation.
7. Ten controlled DEMO trades with 10/10 reconciliation and zero orphan/state mismatches.
8. Longer demo-forward validation.

Profit is not the execution-certification criterion.

## Execution telemetry
Record strategy/version, setup DNA, signal time, order time, fill time, spread, slippage, requested/filled volume, SL/TP, MAE/MFE where available, exit reason, realized result, Risk Governor state and reconciliation status.

## Cloud constraint
Keep execution self-contained. External ASTRA/NVIDIA/Supabase services remain research/observability systems and must not be a hard dependency for entry, protective stops, exits or emergency risk controls.

LIVE remains locked in both policy and executable code. Removing the live-account stop requires a separate reviewed release after native compile/backtest, reconciliation certification, and forward validation.
