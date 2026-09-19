# AUREON Ω

Market Intelligence & Opportunity Engine · ASTRA Intelligence Engine

This is a source-preserving migration candidate. It is **not deployed** and has no configured AI, Supabase or market-data credentials. A dedicated Supabase project is now active with foundation, monitoring and index migrations applied. GitHub/Vercel publication remains blocked on account authentication.

## What is implemented

- Preserved React/TypeScript mobile scanner: 1–4 chart images, five analysis roles, six strategy families, ranked conditional opportunities and evidence display.
- Vercel Node API adapter replacing the original hosting SDK; configurable OpenAI/OpenRouter vision provider with strict output validation and timeouts.
- Supabase owner authentication; API verifies the user and enforces one owner UUID. No public AI calls.
- Signed, expiring analysis-stage envelopes bound to user, stage and scan. Client-supplied canonical data and specialist reports are not trusted.
- Server-owned immutable scan records; original canonical evidence, chart hashes and final result stored together. Images remain transient and are sent only to the configured AI provider.
- SQL schema with explicit grants and RLS; distributed per-owner request quota, replay protection and atomic lifecycle event handling.
- Journal UI and append-only user-observed WATCH / INVALIDATED / EXPIRED / CLOSED events. Terminal setups cannot be reopened.
- XAU/USD and BTC/USD reference adapters. Quote sources and unknown freshness are disclosed; BTC/USD is never renamed BTC/USDT.
- Unsupported numeric plan levels are removed. Risk/reward is recalculated from supported levels, never taken from AI claims.

## Execution authority

All scenarios are conditional. The source prototype allowed a sufficiently high score to mark a screenshot plan executable. This migration deliberately removes that authority: screenshots cannot establish current broker bid/ask, fresh closed-candle triggers or actual spread. The app places **zero broker orders**.

Readiness is deterministic arithmetic over AI-classified gates. It is not an independently verified strategy signal, probability, win rate or demonstrated edge. There is no fabricated market feed or sample trading result in the product. Artificial numeric fixtures exist only in automated safety tests.

## Local verification

Node 22.18+:

```sh
npm ci
npm test
npm run build
```

For development, load server environment variables securely and run `npm run dev:api` and `npm run dev` in separate terminals. `npm run dev` proxies `/api` to port 3001. The UI safely shows setup incomplete without configuration.

## Deployment sequence

1. Create a private `aureon-omega` repository in the intended GitHub account, then push this source and lockfile.
2. Confirm the Supabase organization and quoted project cost before creating a dedicated project. Do not repurpose unrelated projects.
3. For a new database, apply the versioned files in `supabase/migrations/` in chronological order. They have already been applied to the dedicated project; do not replay them there. Run the SQL advisor and hosted RLS tests afterward.
4. Create the owner in Supabase Auth; disable public signup. Record the owner's actual user UUID as `OWNER_USER_ID`.
5. Import the GitHub repository in Vercel with the Vite preset. Set the server environment values listed in `.env.example`; no secret gets a `VITE_` prefix. Use Supabase's modern `sb_secret_...` server key as `SUPABASE_SECRET_KEY`; the legacy service-role key is accepted only as a compatibility fallback. Generate a random signing key of at least 32 bytes.
6. Select a genuinely available vision model that supports strict JSON-schema output. Provider/model choice and credentials have not been verified in this migration.
7. Deploy a preview. Verify authentication, provider failure states, one real chart scan, journal persistence, ownership isolation, and data-source identity. Only then promote the verified deployment.

The Vercel Git integration handles future deployments. CI runs the safety suite and production build. Configure required CI checks before merging. Hosting/account secrets are never stored in the repository.

## Known unfinished work

- Supabase migrations and grants are verified remotely; security advisors are clear. Hosted AI and Vercel integration tests still require credentials and deployment access.
- Browser QA remains blocked because the cloud browser cannot access the local preview. The live Kraken adapter check timed out; no feed health is claimed.
- Real closed-candle acquisition and price-path monitoring are implemented, including gap/freshness checks, unknown intrabar ordering, immutable candle evidence and observation counts. Automatic strategy qualification and broker quote authority remain unimplemented. The protected scheduler endpoint is wired to a daily Vercel Cron (`0 0 * * *`), compatible with Hobby scheduling. It reconstructs the closed-candle observation window from provider history; it does not imply continuous tick monitoring. No fill or trading P&L is inferred.
- Forward-validation statistics remain unavailable until a verified outcome dataset exists. Price-path state counts are available, but win rate, expectancy and profit factor intentionally remain null until genuine execution-quality outcomes exist. No backtest or profitability claim is made.
- Auth tokens are held in memory; refresh requires signing in again. Password reset/MFA and account recovery use the provider console pending a dedicated UI.
- Only the latest 50 scans and 100 lifecycle events are displayed. Older rows remain stored; pagination is a follow-up.
- There is no chart-image archive, Storage bucket or retention cleanup worker. Only canonical evidence and hashes persist.
- The recovered stored version contains six strategy families and up to four scenarios. Earlier conversation claims of a 12-family V3 were not present in recoverable source and are not represented as implemented.

See `docs/ARCHITECTURE.md` and `docs/VERIFICATION.md` for the audit and remaining gates.
