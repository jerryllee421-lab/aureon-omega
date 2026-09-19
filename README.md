# AUREON Ω

**Market Intelligence & Opportunity Engine · ASTRA Intelligence Engine**

AUREON Ω is a production-deployed, mobile-first market-intelligence workspace for conditional Gold and Bitcoin analysis. It is analysis-only and implements zero broker order execution.

## Production stack

- React + TypeScript + Vite on Vercel.
- ASTRA uses `openai/gpt-5.6-sol` through Vercel AI Gateway + short-lived Vercel OIDC.
- Privileged database calls use Vercel OIDC → Supabase Edge Function → Supabase server credential.
- Analysis-stage proofs are signed/verified inside the Supabase Edge service.
- Supabase owner authentication + owner-scoped RLS.
- Private-schema replay/quota ledger.
- GitHub Actions tests/build gate every main-branch release.

## Intelligence

- 1–4 chart screenshot pack.
- Vision + Structure Analyst + Opportunity Analyst + Risk Critic + Lead adjudication.
- Six strategy families and up to four ranked conditional scenarios.
- Deterministic readiness and numeric-provenance hardening.
- Native M5/M15/H1/H4 closed-candle quant context: EMA20/50, RSI14, ATR14, ADX14, range, structure, regime and MTF alignment.
- BTC data truth cross-checks Coinbase and Kraken reference data; Gold reference data is optional through Twelve Data.

## Authority boundary

Screenshot, exchange-reference and quant data never create broker execution authority. Entry/SL/TP values survive only when exact numeric evidence is supported. No fills, slippage, realized P&L, win probability or profitability are inferred.

## Research boundary

Research reports sample counts, lifecycle states, provider errors and favorable/adverse reference-path excursions. Win rate, expectancy and profit factor remain null until an execution-quality outcome dataset exists.

## Production environment

Required: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `OWNER_USER_ID`, and `CRON_SECRET` for scheduled monitoring. `TWELVE_DATA_API_KEY` is optional for Gold.

Vercel production does not require long-lived `AI_API_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `PIPELINE_SIGNING_KEY` under the active OIDC architecture.

## Release gate

CI tests PASS → CI build PASS → Vercel READY → `/api/health` HTTP 200 with `ready:true`.

See `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, and `docs/VERIFICATION.md`.
