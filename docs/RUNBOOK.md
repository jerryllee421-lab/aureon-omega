# AUREON Ω Production Runbook

## Release gates
1. GitHub tests pass.
2. TypeScript/Vite build passes.
3. Vercel is READY.
4. `/api/health` returns `ready:true`.
5. Supabase security advisor is reviewed.

## Incident triage
1. `/api/status` — ASTRA/OIDC.
2. `/api/health` — ASTRA + privileged DB bridge.
3. Vercel runtime errors + X-Request-Id.
4. Owner Data Truth — provider conflicts/staleness.
5. Supabase advisor + Edge logs.

## Security
- Production AI and privileged DB access stay OIDC-based.
- Do not restore a long-lived Vercel Supabase admin key without a reviewed migration.
- Rotate `CRON_SECRET` if exposed.
- Client access/refresh tokens remain in memory only.

## Fail-closed
Unavailable provider → UNAVAILABLE. Provider disagreement → conflict. Screenshot/quant context → no execution authority. No fills/P&L inferred from candle touches. Gaps/staleness block conclusions.

## Research
Readiness is deterministic gate arithmetic, not probability. Strategy evidence remains RESEARCH_ONLY until verified execution-quality outcomes exist.
