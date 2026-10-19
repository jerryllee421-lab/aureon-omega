# AUREON XAUUSD MT5 real-tick archive

This is the canonical acquisition lane for a persistent minimum two-year tick dataset. It uses the official MetaTrader 5 terminal under Linux/Wine, signs in only to the configured PXBTTrading-1 DEMO account, and calls CopyTicksRange with COPY_TICKS_ALL for 740 calendar days.

## Workflow behavior

1. Installs official MT5 in an isolated, ephemeral Wine prefix on a GitHub Actions Ubuntu runner.
2. Compiles the MQL5 exporter with MetaEditor.
3. Requires DEMO account mode and exactly PXBTTrading-1; the exporter contains no trading functions or order submission.
4. Exports UTC daily CSV shards containing bid, ask, last, volume and tick flags.
5. Validates tick timestamps, spread ordering, and at least 730 days between the first and last observed tick.
6. Creates monthly ZIP archives and publishes them as a GitHub Release. Large binary data is not committed to Git history.

## One-time repository setup

In GitHub repository Settings → Secrets and variables → Actions → Repository secrets, add:

- MT5_DEMO_LOGIN — numeric demo login
- MT5_DEMO_PASSWORD — demo password
- MT5_DEMO_SERVER — exactly PXBTTrading-1

Never paste secrets into chat. The workflow fails closed if a secret is missing or the server differs. Secret values are not printed or included in release assets. If the account cannot access the historical tick range, coverage validation must fail instead of publishing partial data.

## Run

Open Actions → AUREON MT5 Real-Tick Archive → Run workflow on the branch containing this workflow. It may take several hours. On success, the release is named xauusd-real-ticks-<run_id> and contains one ZIP per UTC month plus coverage metadata.

## Reuse in future tests

Use the latest xauusd-real-ticks-* release as the pinned historical source and verify manifest plus SHA-256 values before importing. Existing Dukascopy M1 mirror data and OHLC bars must not be represented as MT5 real ticks.

Important: release assets are public because this repository is public. They contain market ticks, not credentials or account identifiers. Broker history coverage can vary by account, server, symbol and retention policy. A successful archive proves acquisition and validation; it does not alone prove an MT5 Strategy Tester consumed the archive. Custom-symbol/native tester import must be explicitly validated before calling downstream results real-tick backtests.
