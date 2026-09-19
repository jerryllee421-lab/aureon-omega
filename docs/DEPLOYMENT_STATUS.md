# AUREON Ω deployment status — 2026-09-19

## Ready
- Production migration source recovered.
- Dedicated Supabase project: `hfjglluombfnrwslfbuw` (`aureon-omega`) is ACTIVE_HEALTHY.
- Foundation, monitoring and foreign-key-index migrations are applied.
- All public tables use RLS; Supabase security advisor currently reports zero security lints.
- Vercel-compatible API adapter is present.
- Protected `/api/cron/monitor` endpoint is present.
- `vercel.json` now declares a daily cron (`0 0 * * *`) suitable for Vercel Hobby. The monitor reconstructs closed-candle history and does not claim tick-level monitoring.
- GitHub Actions CI workflow is included.

## External activation still required
1. Create private GitHub repository `aureon-omega` (current GitHub connector cannot create repositories).
2. Push this package and import the repository into Vercel (current Vercel connector deployment action returns `tool not found`).
3. Create the single owner user in Supabase Auth, then set its UUID as `OWNER_USER_ID` in Vercel.
4. Configure server-only Vercel environment variables from `.env.example`.
5. Deploy Preview, run real owner-login/chart/provider QA, then promote to Production.

## Environment variables
- `AI_API_KEY` — secret; required for ASTRA chart inference.
- `AI_MODEL` — selected vision-capable model supporting the schema.
- `AI_BASE_URL` — defaults to OpenAI-compatible endpoint.
- `SUPABASE_URL` — dedicated AUREON project URL.
- `SUPABASE_PUBLISHABLE_KEY` — public client-safe key.
- `SUPABASE_SECRET_KEY` — preferred modern `sb_secret_...` server-only key. Legacy `SUPABASE_SERVICE_ROLE_KEY` remains a temporary compatibility fallback.
- `OWNER_USER_ID` — Supabase Auth UUID for the single owner.
- `PIPELINE_SIGNING_KEY` — secret, >=32 random bytes.
- `TWELVE_DATA_API_KEY` — optional; enables Gold reference data.
- `CRON_SECRET` — secret, >=32 random bytes; Vercel Cron auth.

## Truth boundary
The forward monitor records provider candle-path observations only. It does not infer broker fills, spread, slippage, realized P&L, win rate, expectancy or profit factor without a verified execution dataset.
