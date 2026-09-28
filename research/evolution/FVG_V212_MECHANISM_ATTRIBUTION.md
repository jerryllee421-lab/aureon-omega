# FVG V2.12 Mechanism Attribution Campaign

## Objective
Explain the historical V2.12 high-growth results causally before adding complexity. The R943K and R1.253B records remain immutable historical controls, not forward/live evidence.

## Control
Use the exact V2.12 EA and the exact historical preset/report pair when available. No mutation may change more than two causal variables.

## Ordered experiments
1. **Re-entry / zone recycling**
   - Control: repeated trading enabled.
   - Ablation A: one trade per FVG.
   - Ablation B: repeated trading + cooldown.
   - Measure trade count per zone, expectancy by attempt number, PF, DD, losing streak, MFE/MAE.
2. **Rejection**
   - Control: rejection required.
   - Ablation: rejection disabled.
   - Measure incremental expectancy and adverse excursion.
3. **Displacement / FVG quality**
   - Sweep MinFVG_ATR and MinBody_ATR locally around control; do not optimize holdout.
   - Report neighbor stability, not best point only.
4. **Direction asymmetry**
   - Long-only, short-only, combined.
   - No directional winner is promoted without validation/holdout persistence.
5. **Exit management**
   - Profit locks on/off.
   - ATR trail on/off.
   - Fixed terminal target comparison.
   - Attribute realized R distribution and tail dependence.
6. **Compounding attribution**
   - Repeat identical trade logic with auto-compounding off.
   - Compare R-space metrics separately from currency terminal balance.
7. **Execution stress**
   - Spread buckets, slippage shocks, delayed entry and MT5 real ticks.

## Required reporting
For every experiment: parent ID, mutation variables, dataset hash, period, trade count, PF, expectancy R, net R, max DD R/%, win rate, long/short, session, year, attempt number per FVG, MFE/MAE, Monte Carlo and holdout result.

## Decision rule
Headline currency profit never promotes a candidate. A mechanism survives only if its incremental contribution persists OOS, is neighbor-stable, survives realistic costs and eventually reproduces under native MT5 real ticks.
