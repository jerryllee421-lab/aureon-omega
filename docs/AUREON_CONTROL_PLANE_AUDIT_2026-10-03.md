# AUREON Ω — Control-Plane Audit (2026-10-03)

## Verified strengths

- Production Vercel deployments are currently healthy; recent production releases are READY and no production error/fatal runtime logs were observed in the audited 24-hour window.
- The repository already separates baseline EAs, challengers, research, cTrader Cloud, cTrader Open API, IG DEMO, tests, Supabase, and CI workflows.
- The research evolution policy already requires holdout positivity, neighbor stability, cost stress, walk-forward validation, and native MT5 real ticks before DEMO forward promotion.
- Supabase `aureon-service` uses custom Vercel OIDC verification, pins team/project/environment, allowlists database paths, and signs short-lived stage proofs.

## High-priority gaps

1. **Research evidence is not first-class production data.** The research lineage tables were empty during the audit, so strong MT5/Python evidence is not yet represented in the governed store.
2. **Broker lanes are fragmented.** MT5, cTrader Cloud/Open API, and IG DEMO should converge on one immutable research/evidence contract. Broker adapters should not redefine strategy logic.
3. **Repository/database migration drift exists.** Production Supabase includes a 2026-09-27 live-project-monitor migration that is not present under `supabase/migrations` on `main`.
4. **V9.3 is not yet under repository/CI governance.** It remains a research artifact pending MetaEditor compile and native real-tick evidence.
5. **Supabase security/performance debt exists.** Three service-oriented tables have RLS enabled with no client policies (fail-closed but undocumented), leaked-password protection is disabled, and four owner-read policies have per-row auth evaluation warnings.

## Improvement contract

`dataset hash -> experiment config -> run -> raw evidence hashes -> validation-only candidate selection -> untouched holdout -> half-year stability -> cost/neighbor stress -> MT5 real-tick parity -> DEMO canary`

No AI model, indicator stack, or broker adapter may bypass those gates.

## Immediate changes

- Add a canonical V9.3 evidence importer.
- Hash all research inputs.
- Select challengers on VALIDATION only.
- Read HOLDOUT only after selection.
- Preserve CONTROL as variant 0.
- Add an execution-free CI safety gate around research evidence tooling.

## Remaining engineering gates

- Compile V9.3 with 0 errors / 0 warnings.
- Run XAUUSD M5 native real ticks and ingest all V9.3 evidence CSVs.
- Reconcile Supabase migration history into Git.
- Replace direct long-lived research publishing credentials with an explicit OIDC research-ingress path.
- Define one immutable TradeIntent/ExecutionEvidence contract across DEMO adapters.
- Keep LIVE execution prohibited until a separate explicit certification program exists.
