# Verification record

## Completed locally

- Production Vite build and TypeScript check across frontend, API, backend and server helpers.
- 16 automated tests pass, including an embedded real Postgres engine (PGlite) executing the entire SQL schema.
- RLS rejects another user's reads and denies anonymous reads. Authenticated client writes and privileged RPC calls are rejected.
- Stage claims enforce ordering, duplicates and hourly quota. Lifecycle events enforce ownership and reject reopening terminal setups.
- Signed evidence rejects modification, cross-user reuse, wrong role and expiry.
- Maximal AI gate scores never enable execution. Unsupported targets are removed; wrong-sided stops block RR; conflicting instruments clear scenarios.
- Unconfigured HTTP API returns blocked status and denies journal access.

## Not yet verified

- Owner login, live chart inference and application-to-Supabase persistence. Migrations are applied remotely; security advisors are clear and owner SELECT-only grants were verified.
- Vercel build/runtime/preview routing on the actual hosting platform.
- Browser visual and interaction QA at mobile/desktop widths, keyboard accessibility and chart upload flow.
- Live-provider availability from the deployment region.
- No real trading performance or automated forward monitoring has been validated.

## Release checklist

1. Create dedicated cloud resources and securely configure environment variables.
2. Apply schema; run hosted owner/non-owner access checks and Supabase advisors.
3. Confirm provider/model supports vision and the supplied strict schemas.
4. Upload a real chart pack, complete inference, reload the journal and verify the saved evidence.
5. Attempt tampered stage payloads; confirm rejection. Confirm no broker execution endpoint exists.
6. Check all unavailable/stale data states and ensure BTC/USD remains distinct from BTC/USDT.
7. Test mobile layouts and keyboard controls before production promotion.

## Continuation checks

- Supabase project `hfjglluombfnrwslfbuw` is active in eu-west-1 at a quoted project cost of $0/month.
- GitHub CLI 2.101.0, Vercel CLI 59.23.2 and Supabase CLI 2.117.0 are installed in the build workspace. Their account authentication is separate from plugin authentication.
- Six additional tests cover candle closure, gaps, staleness, invalid geometry, same-candle ambiguity and non-fabricated observation summaries.
- Live Kraken check timed out. Local browser preview returned ERR_BLOCKED_BY_CLIENT; neither was treated as a pass.
- No new repository, Vercel deployment, owner Auth user, or AI credential was created. The source now includes a daily Vercel Cron declaration for `/api/cron/monitor`; it becomes active only after deployment and `CRON_SECRET` configuration.
