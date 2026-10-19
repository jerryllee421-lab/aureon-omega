# Cost-stress protocol

The cost-stress wrapper runs the same walk-forward framework at a set of flat
basis-point cost floors. Each scenario reclassifies UP/DOWN/NEUTRAL outcomes using
that cost threshold and subtracts the same assumed cost from the simple PnL proxy.

Use this as a sensitivity screen only. It does not model the time-varying bid/ask
spread, commission per lot, slippage distribution, gaps, rejected orders, partial
fills, or broker-specific XAUUSD contract rules. A candidate that only works at
the lowest cost assumption should not pass promotion gates.

For a valid comparison, hold forecast timestamps, horizon, stride, lookback,
minimum evidence, and other parameters fixed. Do not choose the best cost grid or
threshold based on the final untouched holdout.
