# V2.17 native compile gate

This folder preserves the V2.17 source control and three isolated V2.18 research challengers for **compile-only** validation.

- V2.17 is an unchanged historical control. It does not contain the challengers' early real-account gate and must not be attached to a live account.
- V2.18 challengers fail initialization unless running in Strategy Tester or on a DEMO account. They are not certified profitable.
- This workflow compiles source files only. It does not connect to a broker, run a Strategy Tester backtest, or send orders.
- Compile success is not strategy validation. Native backtests still require matched XAUUSD history, settings, reports and journals.

The risk-normalized challenger uses a fixed ZAR 1,000 reference balance, 0.50% nominal risk, no compounding, and a 2.0-lot ceiling. Confirm deposit currency and broker symbol specifications before any future DEMO test.
