# AUREON MT5 Adapter — Broker Intelligence & Tester Control

## Scope
This adapter connects to a locally installed MetaTrader 5 terminal using the official MetaTrader5 Python package. It reads terminal/account state, broker symbol specifications, quotes, open exposure and can create a Strategy Tester INI file. Optional market-order submission is guarded and **disabled by default**.

The adapter does not log in to the broker, store passwords, install an EA, certify broker reliability, or claim profitability. Open MT5 manually and sign in to the intended account.

## One-click setup
Run `AUREON_ONE_CLICK_MT5_SETUP.cmd` from the project root. It installs the Python environment under `.venv`, places the adapter at `scripts/mt5_adapter.py`, and preserves an existing `config/mt5_adapter.json`.

Root expected by the initial bootstrap:
`C:\Users\jerry\OneDrive\Desktop\AUREON - AI TRADING`

## Read-only diagnostics
From the root folder:
- `.venv\Scripts\python.exe scripts\mt5_adapter.py doctor`
- `.venv\Scripts\python.exe scripts\mt5_adapter.py status`
- `.venv\Scripts\python.exe scripts\mt5_adapter.py symbols --filter gold`
- `.venv\Scripts\python.exe scripts\mt5_adapter.py quote --symbol XAUUSD`
- `.venv\Scripts\python.exe scripts\mt5_adapter.py positions`

If the broker uses a suffix/prefix, discover it with the symbols command and use the exact broker symbol. Set `terminal_path` in the config only if auto-discovery fails.

## Strategy Tester
Generate a configuration only:
```cmd
.venv\Scripts\python.exe scripts\mt5_adapter.py tester --expert "Exact EA Name" --symbol XAUUSD --period M1 --start 2026-01-01 --end 2026-01-31 --model real_ticks
```
Review `runtime\mt5\strategy_tester.ini` before launch. Launch requires explicit flags:
```cmd
.venv\Scripts\python.exe scripts\mt5_adapter.py tester --expert "Exact EA Name" --symbol XAUUSD --period M1 --start 2026-01-01 --end 2026-01-31 --model real_ticks --run --confirm
```
MT5 must have the EA installed and its tester inputs available. The INI uses MT5's tester model 4 for every tick based on real ticks. Availability and completeness of broker-native real tick history must be checked inside MT5; this adapter does not manufacture missing history.

## Guarded order interface
Order sending is disabled in the shipped config. Do not enable either order flag until the account, broker, symbol, tick-value calculations, SL/TP distance and risk behavior have been independently validated. The adapter requires explicit mode, fresh quote, spread cap, broker volume-step validation, SL/TP, risk estimate, successful order_check and a typed final confirmation. LIVE additionally requires the explicit live config flag, `--confirm-live`, and a typed risk acknowledgement. This is not a substitute for broker-side protections or independent review.

A conservative default spread cap of zero deliberately blocks orders until the user configures a verified cap appropriate to the broker's point convention. Never store account passwords in this project.

## Generated evidence
- `reports\mt5_doctor.json`
- `reports\broker_intelligence.json`
- `reports\broker_symbols.json`
- `reports\latest_quote.json`
- `reports\open_exposure.json`
- `reports\last_order_check.json` and `last_order_result.json` when an order workflow is explicitly run
- `reports\strategy_tester_last.json`
- `logs\mt5_adapter.log`

## Limitations / release gates
This source has not been executed on the user's Windows PC or against the user's broker. MT5 terminal connectivity, the exact broker symbol, real tick availability, tester launch, EA compilation, and any order execution remain unverified until local evidence is reviewed. Do not describe the adapter as production-certified before those tests pass.
