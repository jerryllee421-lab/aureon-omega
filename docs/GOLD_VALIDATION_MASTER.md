# AUREON Ω Gold Validation Master

## Frozen control

The authoritative high-growth control is `FVG_V2_12_R943K`.

Recorded MT5 result:
- XAUUSD M1, 2026-09-01 through 2026-09-24
- Every tick based on real ticks, 100% history quality
- Initial deposit: ZAR 800; leverage: 1:100
- Net profit: ZAR 942,349.65
- Profit factor: 2.58
- Trades: 1,135
- Win rate: 64.41%
- Relative equity drawdown: 21.55%

The source EA is preserved unchanged. The benchmark-specific tester overrides are stored separately in `ea/baseline/presets/FVG_V2_12_R943K.set`.

## Development law

No later EA replaces the control because it is newer or more complex. A challenger is promoted only when evidence shows a material improvement after controlled ablation.

Required sequence:
1. Reproduce the frozen control under the recorded benchmark.
2. Run same-period parity.
3. Run untouched out-of-sample periods.
4. Walk-forward by chronological blocks.
5. Stress spread, slippage, latency, symbol specification and execution failures.
6. Monte Carlo realized-R paths.
7. Validate BUY/SELL, session and regime dependence.
8. Validate parameter-neighbour stability.
9. Native MT5 real-tick verification is mandatory before any promotion.
10. Demo forward validation is mandatory before any live-risk discussion.

## Active lanes

- **V2.12 frozen control:** source of truth for the R943K benchmark.
- **Python Gold Research Lab:** deterministic approximation for discovery only; never treated as MT5 tick-equivalent.
- **ASTRA campaign EA:** experimental challenger lane; no promotion without native tester evidence.
- **cTrader Cloud:** demo certification/parity lane; live use remains locked until native cTrader validation and reconciliation pass.

## Non-negotiable interpretation

The R943K result is a historical backtest result, not a forecast and not proof that equivalent compounding will survive other periods, brokers, symbol specifications or live execution.
