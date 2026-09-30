# AUREON Ω cTrader Open API DEMO lane

Linux-native independent validation/fallback lane for the V2.17 forward-certification program.

## Current authority

The current `executor.py` is a **zero-order broker preflight**. It authenticates against cTrader DEMO, verifies the specifically configured Pepperstone DEMO account, resolves XAUUSD and broker symbol specifications, verifies FULL_ACCESS account rights, subscribes to a fresh spot quote, records safe preflight evidence, and exits.

It contains no order-submission message types and refuses to run when `AUREON_EXECUTION_ENABLED=true`.

The deterministic V2.17 strategy, Risk Governor and restart-durable canary state modules are retained and tested independently. They are not yet wired to broker order submission.

## Safety contract

- DEMO endpoint only: `demo.ctraderapi.com:5035`
- refuses any environment other than `demo`
- execution defaults OFF and zero-order preflight hard-blocks execution ON
- specifically configured account ID required; no ambiguous first-account selection
- `isLive == false` required
- Pepperstone broker mapping required
- FULL_ACCESS account rights required
- exact normalized XAUUSD symbol match required
- enabled symbol trading mode required
- broker volume specification must be valid
- fresh spot quote required (<= 3 seconds)
- credentials are environment variables / GitHub Actions secrets only
- no credential values are printed
- no order-capable Open API request types exist in the preflight module

## Secure GitHub Actions preflight

The workflow checks for these repository secrets without printing their values:

- `CTRADER_CLIENT_ID`
- `CTRADER_CLIENT_SECRET`
- `CTRADER_ACCESS_TOKEN`
- `CTRADER_ACCOUNT_ID`

If any are absent, it emits `BLOCKED_MISSING_SECURE_SECRETS` and skips broker authentication.

If all are present, it runs the zero-order Pepperstone DEMO preflight and requires a `PREFLIGHT_PASS` record.

Do not reuse credentials that have previously been exposed in chat, screenshots or logs. Rotate them first and store only fresh values in the secure secret store.

## Runtime

Python 3.11+ on Linux.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# populate secrets OUTSIDE git
python executor.py
```

## Promotion boundary

A successful zero-order preflight proves broker authentication, DEMO/account mapping, symbol resolution and live market-data access only.

It does **not** prove order submission, fills, reconciliation or execution certification. Native cTrader Cloud remains the primary execution route for the five-trade DEMO canary until the Open API adapter is separately completed and certified.
