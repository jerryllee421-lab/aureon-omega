# Quantum Nexus Unified Trading Core

## Status
This change introduces a deterministic, decision-only integration contract joining ASTRA evidence, Opportunity Hunter setup qualification, and Daily Profit Protection. It does not connect a broker, submit orders, or enable live trading.

## Flow
1. ASTRA evidence supplies instrument, direction, scenario status, source timestamp, closed-candle and price-evidence states, readiness score, and contradictions.
2. Opportunity Hunter requires a READY/QUALIFIED directional setup, verified evidence, valid entry/stop/target geometry, minimum readiness score, and minimum reward-to-risk.
3. Daily Profit Protection compares current equity with starting equity. The research default objective is 0.5% of starting equity. The independent 2.0% daily loss limit is a research default and must be calibrated to the explicit account/risk requirements.
4. Durable lockout: callers must load account-scoped daily state from durable storage. When a new objective/loss lockout is reached, persist it before treating the lockout as durable. If persistence is unavailable or unknown, qualification fails closed.
5. Instrument boundary: XAUUSD is the only instrument eligible for the initial workflow. BTCUSD is isolated research-only.
6. Execution boundary: every result returns executionAuthority NONE and liveTrading BLOCKED. A separate explicitly authorized DEMO adapter and broker-account identity check would be required before any order routing exists.

## Verified versus assumed
- Implemented here: deterministic gate logic; 0.5% objective calculation; independent 2.0% loss-limit calculation; unverified evidence blocks; BTC isolation; explicit absence of execution authority.
- Configuration assumption: 2.0% daily loss limit is a research default, not a verified account mandate.
- Not implemented here: durable database writes, broker/account identity verification, order routing, MT5 compilation, historical backtests, or forward DEMO execution.
- Not claimed: profitability, win rate, expectancy, or successful trade execution.

## Integration sequence
- Wire the pure evaluator into the existing scan/monitor response path without changing ASTRA source-evidence authority.
- Persist daily state per account and broker-local date using an atomic transaction/upsert so lockouts survive restarts.
- Add explicit account-mode and symbol allowlist checks in a DEMO adapter. Never infer DEMO from a UI setting alone.
- Journal each gate decision and lockout transition.
- Test restart recovery, duplicate submissions, market-closed responses, broker clock skew, spread/slippage bounds, and daily rollover.
- Require CI tests/build, Vercel readiness, then broker-side DEMO forward evidence before enabling any DEMO order adapter.

## Safety invariants
- No order submission occurs in this package.
- No LIVE authority can be returned.
- Unknown, unavailable, degraded, contradictory, stale, or invalid evidence cannot qualify a scenario.
- Daily objective and daily loss limit are independent and both block new qualification.
- A decision is not a fill, realized P&L, or a profit guarantee.
