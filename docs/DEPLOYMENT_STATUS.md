# AUREON Ω deployment status — 2026-09-19

## Verified production

- GitHub private repo + CI active.
- Vercel production deployed at `aureon-omega.vercel.app`.
- ASTRA OIDC → Vercel AI Gateway verified.
- Vercel OIDC → Supabase Edge privileged service verified.
- `/api/health` returns `ready:true` with database ready.
- Owner-only RLS and private replay/quota schema active.
- Native MTF quant, Research, Journal, Monitor and Data Truth views deployed.
- Protected daily Vercel Cron endpoint deployed.

## Production environment

Required: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `OWNER_USER_ID`, `CRON_SECRET`.

Optional: `TWELVE_DATA_API_KEY` for Gold reference/quant data.

Obsolete long-lived Vercel AI/Supabase-admin/pipeline keys are not required by the active OIDC runtime and can be removed after operator verification.

## Remaining operator-only action

Rotate `CRON_SECRET` if any previous value was exposed outside the secret manager. Never paste its replacement into chat.
