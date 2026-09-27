# MT5 V2.12 -> cTrader Cloud parity map

Source authority: FVG_Scalper_V2_12_Research.mq5.

| MT5 behavior | cTrader implementation | State |
|---|---|---|
| Three-candle FVG + displacement direction | UpdateZoneOnNewBar | PORTED |
| Min FVG ATR / body ATR / body ratio | Parameters + scan | PORTED |
| Newest-zone replacement | UpdateZoneOnNewBar | PORTED |
| Closed-bar zone invalidation | EvaluateFvgRetest | PORTED |
| Tick retest inside zone | EvaluateFvgRetest | PORTED |
| Current-bar rejection >=0.55 / <=0.45 | CurrentBarRejection | PORTED |
| SL beyond FVG by 0.15 ATR | TryEnter | PORTED |
| Max SL <=3 ATR | TODO parity guard | REQUIRED |
| TP = 30R | TryEnter | PORTED |
| 0.5R -> +0.1R lock | ManagePosition | PORTED |
| 1.0R -> +0.35R lock | ManagePosition | PORTED |
| 1.5R -> 0.1 ATR trail with +0.35R floor | ManagePosition | PORTED |
| Exact MT5 volume/risk semantics | cTrader fixed-risk sizing | NEEDS SYMBOL PARITY TEST |
| Report override OneTradePerFVG=false | certification build currently true | INTENTIONALLY LOCKED |
| MT5 margin preflight semantics | Risk Governor scaffold | NEEDS CTRADER PARITY |
| Persistence/restart restoration | not complete | REQUIRED |
| Full MFE/MAE/slippage telemetry | not complete | REQUIRED |

## Rule
No item marked NEEDS/REQUIRED may be described as parity-complete. The certification build keeps re-entry disabled until the one-trade behavior matches the control closely enough to isolate platform semantics.
