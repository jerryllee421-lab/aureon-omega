# AUREON Ω deployment status — 2026-09-28

## Verified production

- GitHub repository: `jerryllee421-lab/aureon-omega`, public, with `main` as production authority.
- Vercel project `aureon-omega` is deployed and the checked production deployment is `READY`.
- No Vercel runtime errors were returned for the checked seven-day window.
- Supabase project `hfjglluombfnrwslfbuw` is `ACTIVE_HEALTHY` in eu-west-1.
- Supabase `aureon-service` Edge Function is active.
- Project-monitor evidence tables are RLS-protected and intended for server/service access.
- Vercel SSO protects the currently checked deployment endpoints; anonymous `/api/health` and `/api/status` probes redirect to authentication and must not be reported as application failures.

## Runtime boundary

The web application remains an analysis/research system. No browser or web API path is authorized to execute broker trades.

## Research boundary

- V2.12 R943K is the frozen historical control.
- V4 ASTRA Research Accelerator is the primary MT5 challenger.
- cTrader Cloud remains `DEMO_ONLY` and the executable hard-stops when `Account.IsLive` is true.
- Native MT5/cTrader compile, broker-real-tick validation, reconciliation and demo-forward evidence are mandatory before promotion.

## Secrets

Keep all privileged credentials in platform secret stores. Do not commit or paste broker passwords, API keys, service-role secrets or cron secrets into repository source or chat.
