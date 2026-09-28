# AUREON Ω — Gold EA Lineage

This directory contains **challengers**, not production champions.

## Authority order

| Asset | Role | Status |
|---|---|---|
| `ea/baseline/FVG_Scalper_V2_12_Research.mq5` | Frozen historical control | CONTROL — do not mutate |
| `FVG_Scalper_V4_00_ASTRA_ResearchAccelerator_AllInOne.mq5` | Primary MT5 challenger | RESEARCH ONLY |
| `astra-campaign-v1/AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5` | Campaign / ablation challenger | RESEARCH ONLY |
| `ctrader-cloud/AUREONPrimeGoldCloud.cs` | cTrader Cloud parity/certification lane | DEMO ONLY; LIVE HARD-BLOCKED |

## Promotion rule

A challenger is not promoted because it is newer, more complex, or produces a higher single backtest balance. Promotion requires:

1. deterministic same-period control comparison;
2. untouched out-of-sample evidence;
3. walk-forward stability;
4. spread/slippage/execution stress;
5. parameter-neighbour stability;
6. native platform compile and real-tick/backtest evidence;
7. controlled demo-forward validation and reconciliation.

The recorded V2.12 R943K result remains a historical control, not a performance forecast.
