# AUREON Ω — Pepperstone cTrader FIX Demo Adapter

This directory defines the machine-to-machine FIX 4.4 boundary for AUREON forward validation.

## Safety invariants
- DEMO only. The adapter must refuse non-demo hosts/configuration.
- Credentials and account identifiers are environment variables only; never commit them.
- QUOTE and TRADE sessions are independent.
- Order submission is disabled by default with `AUREON_FIX_TRADING_ENABLED=false`.
- V2.17 strategy semantics are frozen; this adapter is transport/telemetry only.
- No live promotion is implied by connectivity or successful demo orders.

## Required environment variables
```
AUREON_FIX_ENV=demo
AUREON_FIX_HOST=demo.cfixapi.com
AUREON_FIX_QUOTE_SSL_PORT=5211
AUREON_FIX_TRADE_SSL_PORT=5212
AUREON_FIX_SENDER_COMP_ID=<secret>
AUREON_FIX_TARGET_COMP_ID=cServer
AUREON_FIX_PASSWORD=<secret>
AUREON_FIX_TRADING_ENABLED=false
```

Session-specific SenderSubID values:
- QUOTE session: `QUOTE`
- TRADE session: `TRADE`

## Bring-up gates
1. TLS connectivity.
2. FIX Logon accepted independently on QUOTE and TRADE sessions.
3. Heartbeat/TestRequest and sequence handling stable.
4. SecurityList resolves broker XAUUSD symbol/security ID.
5. MarketDataRequest produces bid/ask telemetry.
6. ExecutionReport/position reconciliation works.
7. Only then may demo order submission be enabled.
8. Collect 50/100/250/500 completed V2.17 trades for PRIME drift comparison.

Never place credentials in source, logs, artifacts, screenshots, issue bodies, or telemetry.
