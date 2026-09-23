# ASTRA V1 Validation Matrix

The first research cycle is intentionally narrow. The purpose is to determine whether the campaign architecture survives realistic testing, not to maximize a backtest headline.

| Phase | Configuration | Purpose |
|---|---|---|
| A | E1 only | Establish the base setup's standalone edge |
| B | E1-E3 | Measure controlled scaling |
| C | E1-E5 | Measure full campaign contribution |
| D | Fixed 0.10 campaign cap | Compare deterministic sizing |
| E | 1% campaign risk cap | Compare risk-normalized sizing |
| F | London only | Session attribution |
| G | New York only | Session attribution |
| H | London + New York | Combined production candidate |
| I | Spread/slippage stress | Execution robustness |
| J | Out-of-sample | Generalization |
| K | Walk-forward | Parameter stability |
| L | Monte Carlo | Sequence and execution risk |

## Frozen baseline

- Instrument: broker XAUUSD symbol
- Entry TF: M5
- Liquidity TF: M15
- Context: H1 + H4
- Modelling: MT5 real ticks when broker history supports it
- Initial deposit: 10,000 account currency
- Leverage: 1:100 reference profile
- Campaign allocation: 0.10 lots maximum
- Entry tranche: 0.02 lots
- Max entries: 5
- Daily loss stop: 3%
- Equity drawdown halt: 6%
- No martingale
- No grid

## Acceptance evidence

Every run must retain the MT5 tester report, EA CSV event ledger, input set, build SHA, symbol specification, date range, spread/model settings and compiled EX5 hash.

A configuration is not promoted merely because it is profitable. Minimum evidence includes adequate sample size, positive expectancy, controlled drawdown, stable sub-period behavior and acceptable degradation under execution stress.
