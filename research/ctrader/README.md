# cTrader Validation Lane

This directory defines the broker-native validation stage for AUREON Gold research.

Official cTrader CLI capabilities used:
- metadata: inspect cBot parameters
- backtest: server M1 or server ticks
- optimize: bounded genetic/grid parameter search
- JSON/HTML reports and event/log evidence
- persistent data directory for downloaded historical prices

## Required order
1. External Gold Brain candidate passes deterministic Evolution gates.
2. Compile candidate as .NET 8 cBot.
3. Metadata/preflight.
4. M1 backtest sanity check.
5. Tick backtest.
6. Cost/stress and chronological OOS checks.
7. Compare against frozen control on like-for-like assumptions.
8. Only then consider demo-forward.

## Guardrails
- Research/demo only.
- No live-money execution.
- No secrets in repository.
- Optimization is restricted to development data.
- Sealed holdout is evaluation-only.
- A candidate failing reconciliation or evidence integrity is rejected.
