# AUREON Ω Production Runbook

## Release gates
A production change is accepted only when GitHub Actions passes tests and the TypeScript/Vite build, Vercel reports READY, and /api/health returns ready=true.

## Fail-closed rules
- No provider result means UNAVAILABLE, never a fabricated value.
- Screenshot analysis never grants execution authority.
- Broker orders are not implemented.
- Cross-provider disagreement is surfaced, not averaged away as certainty.
- Monitoring observations are reference-market candle paths, not fills or P&L.

## Incident checks
1. Check /api/health and Vercel runtime errors.
2. Check Supabase security advisor and database availability.
3. Check provider-specific status under the owner-only Data truth page.
4. If AI is blocked, verify Vercel OIDC / AI Gateway before adding long-lived API keys.
5. If monitoring is blocked, use the manual owner check; Hobby cron remains daily and coarse.

## Security
- Server secrets stay in Vercel only.
- Owner access is enforced by Supabase user UUID and server verification.
- Client tokens and refresh tokens remain in memory only.
- Rotate any secret exposed outside the secret manager.
- Apply explicit grants for every new database object; default public-schema grants are revoked.

## Research interpretation
Readiness scores are deterministic gate arithmetic, not win probabilities. Strategy research stays RESEARCH_ONLY until a verified execution-quality outcome dataset exists.
