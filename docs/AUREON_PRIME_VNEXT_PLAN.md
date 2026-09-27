# AUREON PRIME — Gold Brain + cTrader Native Validation

## Objective
Build a reproducible Gold research/evolution factory and validate surviving strategies with cTrader's broker-native testing stack before demo-forward promotion.

## Architecture
External XAUUSD BID/ASK M1 -> canonical 21-TF Gold Brain -> Evolution Engine -> deterministic gates -> cTrader CLI tick validation -> demo-forward -> execution telemetry.

cTrader Remote MCP is supervisory/diagnostic. Open API remains the custom execution/telemetry path after application approval. Live-money execution stays disabled.

## Phase 1 — Gold Brain
- Acquire 5y, then 10y, then maximum reliable XAUUSD history.
- Preserve BID/ASK M1, spread and provenance.
- Derive 21 canonical timeframes.
- SHA-256 manifest every canonical dataset.
- Chronological 60/20/20 development/OOS/sealed-holdout partitions.
- Label year/session/trend-range/volatility/spread/shock regimes.

## Phase 2 — Evolution
- Immutable V2.12 R943k historical control.
- Champion/challenger model.
- Max two strategy mutations per experiment.
- Reject insufficient sample, no edge, excessive DD, OOS collapse, parameter cliffs, tail-winner dependence and transaction-cost sensitivity.
- Never optimise on sealed holdout.

## Phase 3 — cTrader native validation
- Port surviving logic to a .NET 8 cBot.
- Build and inspect metadata with cTrader CLI.
- Backtest first with server M1, then server ticks.
- Persist CLI historical data directory between runs.
- Export JSON/HTML reports plus events/logs.
- Validate commission, spread and account/symbol metadata before comparing results.
- Use local CLI optimisation only for bounded parameter neighborhoods; never optimize sealed holdout.

## Phase 4 — Demo certification
- One canary demo trade.
- Then 10 controlled lifecycle trades.
- Require zero orphan positions, zero state mismatches and complete reconciliation.
- Continue demo-forward only after certification.

## Security
No cTrader ID password, Open API client secret, OAuth token or broker credential is committed to Git. Credentials are injected only at runtime. Any secret exposed in chat/screenshots is rotated before use.

## Promotion
No candidate becomes champion from net profit alone. Promotion requires OOS/holdout edge, acceptable drawdown, parameter stability, cost stress, walk-forward evidence and cTrader tick validation.
