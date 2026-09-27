# Execution readiness gates

## Gate A — static safety
- live endpoint disabled
- no committed credentials/tokens
- idempotency key required
- runtime symbol/volume discovery
- one-position / reconciliation invariant

## Gate B — account-info authorization
- cTrader app may still be Submitted
- validate OAuth/account discovery only
- no trading calls

## Gate C — demo trading authorization
Requires cTrader application Active and OAuth trading scope.

## Gate D — one-trade canary
Minimum practical volume. Require quote, submit, ACK, fill, protection, verify, close and deal reconciliation.

## Gate E — ten-trade certification
10/10 reconciled lifecycles; zero orphan positions; zero state mismatches. P/L is not a criterion.

## Gate F — continuous demo
Only after execution telemetry is reviewed. Live remains disabled.
