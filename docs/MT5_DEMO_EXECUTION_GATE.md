# MT5 demo execution gate — integration contract

## Status

The next integration stage is a local, fail-closed account verification layer. It must begin read-only and must not submit trades until terminal identity and risk checks are independently validated on the user's machine.

## Required account identity

- Broker server must match `PXBTTrading-1` exactly.
- Trading symbol must match `XAUUSD` exactly.
- MT5 account mode must explicitly report `DEMO`; missing or unknown mode is blocked.
- A locally configured expected demo login must match the current terminal login.
- Terminal and account trading permissions must both be enabled.

Do not commit passwords, API keys, or other secrets to Git or paste them into chat. Configure account identity locally.

## Fail-closed protections

Default behavior must block execution until explicitly enabled locally. The kill switch must default to active. Require market open, daily loss below the configured 2% limit, fewer than three open positions, and fewer than one pending order. Invalid exposure metrics block. A market-closed response (including MT5 retcode 10018) must stop or throttle retries and never create a tight retry loop.

Before any eventual demo execution, the adapter must refresh account, quote, symbol specification, spread, margin, price, volume, stop-distance, and risk data immediately before each request; apply idempotency and bounded retries; and journal request and broker result. The read-only snapshot must be proven against the intended DEMO terminal before order capability is added.

## Integration stages

1. Build a read-only adapter using the official MetaTrader5 Python package in the isolated AUREON environment.
2. Verify terminal version, connection, server, login, account mode, symbol metadata, tick freshness, market status, positions/orders, equity/balance, and daily P&L.
3. Test all safety gates with mocked MT5 responses; tests must never submit trades.
4. Add the demo execution adapter only after read-only account verification passes. Every order entry point must invoke the safety gate and preserve a global kill switch.
5. Validate with Strategy Tester / native Every Tick Based on Real Ticks, then DEMO forward observation. Live trading remains blocked.

These stages are engineering requirements, not evidence of profitability or successful broker execution.