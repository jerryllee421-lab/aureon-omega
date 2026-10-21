# AUREON Ω XAUUSD Strategy Suite — Implementation Notes

## Scope
This branch adds a single-select MQL5 research EA for four independent XAUUSD strategy candidates: M5 mean reversion, H4 range breakout executed on M5, broker-time session breakout, and daily Candle Range Theory (CRT) using the prior completed D1 candle and M5 sweep/re-entry confirmation. Run each candidate as a separate Strategy Tester pass.

## Safety controls
- DEMO account required by default; EA refuses initialization on a non-demo account.
- Live trading remains blocked.
- 0.25% nominal equity risk per trade; input validation rejects risk above 1%.
- Daily equity loss lock: 2%; peak-equity lock: 6%.
- Maximum spread 80 points, deviation 35 points, maximum 3 entries per broker-server day, 30-minute cooldown.
- Stop-loss and take-profit are attached to each market order. Position sizing uses symbol tick size and tick value; if risk sizing cannot be validated, the trade is skipped.
- Frozen V2.12 benchmark is not modified.

## Candidate defaults (hypotheses, not optimized settings)
- M5 mean reversion: EMA20, RSI14 thresholds 30/70, deviation 1.25×ATR14, only when ADX14 <= 25, reversal candle confirmation.
- H4 breakout: close beyond prior 20 completed H4 bars; buffer 0.10×M5 ATR; M5 ATR stop 1.5× and target 1.5R.
- Session breakout: broker-server 00:00–07:00 range; trade 07:00–17:00; close beyond range plus 0.10×M5 ATR.
- Daily CRT: prior completed D1 candle is the reference range; sweep beyond its high/low and closed M5 candle back inside with directional body.

These are reproducible starting hypotheses, not evidence of optimality. Session hours must be mapped to broker-server timezone and daylight-saving schedule before results are compared.

## Validation protocol
1. Compile with official MetaEditor and archive the source, EX5, compiler log and SHA-256 manifest.
2. Run MT5 Strategy Tester using **Every tick based on real ticks**. Generated ticks and OHLC-only modeling do not qualify.
3. Verify tick coverage and broker symbol mapping (expected XAUUSD; broker may use a suffix).
4. Use identical dates, deposit, leverage, symbol, commission, spread and slippage assumptions for all candidates.
5. First run a one-day plumbing smoke test; do not treat it as performance evidence.
6. Run the common research window and a chronological out-of-sample window. Report PF, net profit, max equity drawdown, recovery factor, trade count, average trade after costs and missing-tick diagnostics.
7. Rank by verified PF only after cost modeling and minimum-sample checks; reject unstable out-of-sample results.
8. V2.12 PF 2.58 and V2.17 PF 2.48 are historical reported values, not current-run verification.

## Known limitations in v1.00
- Strategy Tester execution has not been performed.
- Session boundaries use broker-server time rather than fixed UTC.
- Daily risk state is in-memory and resets on EA initialization; this version does not persist a daily lock across terminal restarts.
- Single active position per symbol and one selected strategy per test.
- Daily CRT uses a strict sweep-and-close-back-inside rule. Alternate CRT variants must be tested separately.
