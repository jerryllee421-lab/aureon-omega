# Production architecture

## Source lineage and scope

Recovered all eleven files from the existing AppDeploy application, latest stored version `1789813239157` (v8, 19 September 2026, 12:20 SAST). Ported the existing component and analysis schemas rather than starting a new application. The prior product name is retired from runtime UI and prompts.

## Runtime boundaries

| Layer | Responsibility | Authority |
|---|---|---|
| React/Vite client | Image compression, MTF uploads, progress, scenarios, journal | Untrusted requests; never stores provider secrets |
| Vercel API | Owner authentication, size validation, signed pipeline, quota, schema checks | Only server can call AI or persist verified pipeline output |
| ASTRA adapter | Vision extraction, three specialist roles, adjudication | Model interpretation, not market truth |
| Authority filter | Exact numeric provenance, RR arithmetic, conflict veto | Screenshot-only; execution always blocked |
| Market adapters | Provider identity and reference timestamps | Reference-only, never broker execution authority |
| Supabase Postgres | Scan evidence and append-only observed lifecycle | Owner read isolation; server-only writes |
| GitHub + CI | Versioned source, tests, production build | Review and deployment source of truth |

The frontend follows the preserved vision → three independent specialists → lead flow. A signed vision envelope includes canonical evidence, user context, scan UUID and image hashes. Specialist proofs bind the report to that exact scan. The lead endpoint reconstructs inputs from proofs and ignores user-modified copies.

## Database contracts

- `scans`: server-generated UUID, owner FK, timestamp, engine version, canonical JSON and final result JSON; composite owner key supports cross-table ownership integrity.
- `setup_events`: composite FK to the owner scan; index within its opportunities; timestamp, state and explicitly USER_SUPPLIED note. No fabricated fill, PnL or probability fields.
- `analysis_claims`: unique owner/run/stage; permits at most 60 claimed stages per rolling hour. Database advisory lock makes quota checking atomic across serverless instances.
- `claim_analysis_stage`: invoker RPC, executable only by service role. Specialist/final stages require a recent vision claim. Replays fail closed. Failed provider attempts consume the claim; start a new scan to retry.
- `record_setup_event`: invoker RPC, executable only by service role. Locks the scan row, checks ownership and valid opportunity index, and prevents reopening a terminal lifecycle.

RLS is enabled on all public tables; anon privileges are revoked; authenticated users receive owner-scoped SELECT only. Both RPCs revoke PUBLIC/anon/authenticated execute. The service role is server-only.

## Provider semantics

An API key is not migrated from the old hosting platform. That platform's native AI service is not portable. The operator must configure their own provider/model. Status reports configuration, not a tested service health guarantee. AI refusals, malformed outputs, HTTP failures and timeouts never substitute generated market data.

Gold references use Twelve Data XAU/USD candles and distinguish stale source timestamps. Coinbase BTC-USD spot responses lack a reliable source timestamp and broker bid/ask, so they remain REFERENCE_ONLY even when a price is returned. Neither adapter verifies an actionable setup.

## Deployment blockers observed

GitHub authentication identifies `jerryllee421-lab`, but repository listing returns none and the exposed connector cannot create repositories. Vercel lists the team and confirms zero projects; calling its exposed deployment operation returns `Tool deploy_to_vercel not found`. No authenticated GitHub/Vercel CLI credentials are available. Supabase now has a dedicated active project with all three migrations applied. The free project cost was confirmed. GitHub browser login was declined and the requested Google option is not displayed; publication is waiting on authenticated access.

## Required next engineering slices

1. Hosted provider and auth QA, then durable evidence persistence under real user credentials.
2. Timestamped OHLC acquisition with continuity, timezone, closed-candle and symbol-identity checks.
3. Explicit deterministic strategy conditions using those candles, with independent risk vetoes.
4. Scheduled lifecycle evaluator with idempotent events, monitoring, and gap-aware real forward outcomes.
5. Metrics only from verified completed samples: sample count, expectancy, drawdown, MAE/MFE and uncertainty; no invented probabilities.

Reference documentation consulted: [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [Supabase changelog](https://supabase.com/changelog), [Vercel Node runtime](https://vercel.com/docs/functions/runtimes/node-js), [OpenAI Chat API](https://developers.openai.com/api/reference/resources/chat). Supabase's change to explicit Data API grants is addressed by the schema's explicit grants.

## Forward monitoring extension

`monitored_setups` stores immutable registered plan levels. `monitor_evidence` stores each evaluated candle batch with its SHA-256 digest and observation. Server updates use optimistic version checks and an atomic RPC. M5 data is accepted only with exact provider identity, positive valid OHLC geometry, chronological continuity and fresh closed candles. Kraken’s final uncommitted row is always removed. Registration starts a 12-hour observation window and requires supported numeric levels with RR >= 1.5. Entry/stop/target touches do not establish trade fills. Unknown intrabar ordering is terminal AMBIGUOUS; missing history is DATA_GAP. Win rate, expectancy and profit factor remain null.

Manual checks use `/api/monitor/check`; `/api/cron/monitor` requires a separate random CRON_SECRET. No scheduler has been provisioned. Configure one only after deployment, server secrets and monitoring QA are complete. Monitor up to 100 recent setups; retain candle evidence for auditing.

Supabase performance advisors initially identified missing composite foreign-key indexes; migration three resolves them. Unused-index informational notices are expected for the empty new database and are not a reason to remove these indexes. [Advisor reference](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index).
