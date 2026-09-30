# AUREON Ω cTrader Open API DEMO executor

Linux-native execution lane for the V2.17 forward-certification canary.

## Safety contract
- DEMO endpoint only: `demo.ctraderapi.com:5035`
- refuses any environment other than `demo`
- execution defaults OFF
- credentials are environment variables only
- XAU-only
- maximum five completed canary trades
- frozen strategy semantics remain in `../ctrader-cloud/AUREONPrimeGoldCloud.cs`
- this adapter is not a new strategy and cannot promote a candidate

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

Set `AUREON_EXECUTION_ENABLED=true` only after authentication/account/symbol preflight passes on the DEMO account.

The service authenticates the application, discovers the authorized account, authenticates that account, discovers the XAU symbol, and maintains the Open API connection. Order execution remains fail-closed until the strategy adapter is certified for semantic parity.
