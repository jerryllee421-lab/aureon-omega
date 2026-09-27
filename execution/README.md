# PRIME Execution Layer
Demo-only cTrader execution workbench.

Design decisions:
- JSON protocol initially for implementation transparency; cTrader JSON endpoint is demo.ctraderapi.com:5036.
- Live endpoint is hard-disabled in configuration.
- Heartbeat target is 9s to stay below cTrader's 10s inactivity guidance.
- Internal request budgets are 40 non-historical and 4 historical requests/s, below documented 50/5 limits.
- Broker symbol IDs are discovered at runtime; never hard-code BTC/XAU IDs.
- Volume is validated against broker symbol metadata before submission.
- Every trade is reconciled through DEAL before the next trade in the ten-trade certification batch.
- Any ambiguity/error halts the batch.
- Credentials/tokens must never be committed or logged.
