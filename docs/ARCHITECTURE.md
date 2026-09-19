# AUREON Ω production architecture

## Trust boundaries

- Client: untrusted image/context requests and in-memory owner session.
- Vercel API: owner verification, orchestration, provider calls, request limits.
- Vercel OIDC: short-lived workload identity.
- Supabase Edge service: strict allowlist for privileged DB/RPC operations and proof signing/verification.
- Supabase Postgres: evidence and lifecycle source of truth.
- ASTRA: interpretation only.
- Authority filter: fail-closed numeric provenance, geometry, RR and contradiction checks.

## OIDC service bridge

Production does not send a long-lived Supabase admin secret from Vercel. Vercel obtains an OIDC token with a custom audience. The Supabase Edge Function validates signature, issuer, audience, exact team ID, exact project ID and production environment before using Supabase-provisioned server credentials.

The same bridge signs 15-minute analysis proofs bound to owner and stage. Cross-user or cross-role proof reuse fails closed.

## Database

Public RLS tables: `scans`, `setup_events`, `monitored_setups`, `monitor_evidence`. Internal `private.analysis_claims` is outside the exposed public schema. Public-schema default privileges are revoked.

## Native context

The Quant view independently derives M5/M15/H1/H4 EMA20/50, RSI14, ATR14, ADX14, range, structure, bias, regime and MTF alignment from closed provider candles. It is not automatically fused into arbitrary screenshots because screenshots may be historical.

## Monitoring

Reference candle paths are checked for identity, geometry, closure, gaps and freshness. Touches are not fills. Same-candle ordering uncertainty is `AMBIGUOUS`. Hobby cron remains daily/coarse; owner-triggered checks are available.

## Non-negotiable exclusions

No broker order endpoint. No fabricated market fallback. No AI probability. No trading P&L inferred from reference touches.
