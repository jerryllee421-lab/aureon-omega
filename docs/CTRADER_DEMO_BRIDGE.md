# AUREON PRIME cTrader Demo Bridge

Status: build-ready; external cTrader application approval pending.

## Invariants
- Demo execution only.
- No credentials in source control.
- Live execution hard-disabled.
- Every order requires an idempotency key and Risk Governor approval.
- First validation is ten controlled lifecycle trades; P/L is not a pass criterion.
- Record quote, submit, acknowledgement, fill, protection, close and deal reconciliation timestamps.
- A failed or ambiguous lifecycle halts the batch until reconciled.

## Secret names
CTRADER_CLIENT_ID
CTRADER_CLIENT_SECRET
CTRADER_ACCESS_TOKEN
CTRADER_REFRESH_TOKEN

Secrets belong in encrypted runtime storage, never GitHub.
