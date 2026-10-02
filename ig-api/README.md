# AUREON Ω — IG DEMO One-Trade Canary

This lane exists to obtain one independently verified automated Gold DEMO trade without a PC, MT5, cTrader, or VPS.

## Safety boundary

- Hard-coded endpoint: `https://demo-api.ig.com/gateway/deal`
- No live IG endpoint exists in this executor.
- Spot Gold only.
- Execution is OFF unless the workflow is explicitly armed.
- Uses the broker-reported minimum deal size for the canary.
- Existing Gold exposure blocks a new order.
- Persistent state blocks any second accepted canary trade.
- Attached stop and limit are mandatory on the submission.

## Strategy gate

The canary only submits after the V7-style M5 exhaustion/liquidity reversal condition qualifies:

- 20-bar liquidity sweep and reclaim
- RSI <= 30 long / >= 70 short
- ADX <= 30
- EMA21 extension >= 2 ATR
- ATR regime ratio in [0.80, 1.80)
- 07:00-12:00 UTC session
- approximately 2.5 ATR stop and 4R target

This is an execution-certification lane, not a claim of future profitability.

## Required GitHub Actions secrets

- `IG_DEMO_API_KEY`
- `IG_DEMO_IDENTIFIER`
- `IG_DEMO_PASSWORD`

Never commit these values to the repository.

## Optional unattended arming

Repository variable:

- `IG_DEMO_CANARY_ARMED=true`

When armed, GitHub Actions checks every five minutes on weekdays. Once one order is accepted, the executor writes `completed=true` to `ig-api/state/one_trade_canary.json`; subsequent scheduled checks halt.

## Workflow

`.github/workflows/ig-demo-one-trade.yml`

Manual dry-run:
1. Actions -> AUREON IG DEMO One-Trade Canary -> Run workflow
2. Leave `execute=false`

Manual armed check:
1. Run workflow
2. Set `execute=true`

Unattended one-trade automation:
1. Add the three IG DEMO secrets
2. Add repository variable `IG_DEMO_CANARY_ARMED=true`
3. The scheduler polls until one V7 signal qualifies
4. It submits the minimum-size DEMO Gold order
5. It polls `/confirms/{dealReference}`
6. It persists the accepted evidence and permanently blocks trade #2
