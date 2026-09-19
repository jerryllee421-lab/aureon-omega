# AUREON Ω

Production-oriented migration candidate for the AUREON Ω Market Intelligence & Opportunity Engine.

## Core properties

- Mobile-first multi-timeframe chart scanner.
- ASTRA intelligence layer with strict structured output.
- Fail-closed deterministic authority gates.
- Owner-only Supabase authentication and persistence.
- Signed pipeline evidence.
- Forward setup monitoring using closed-candle provider history.
- Vercel-compatible serverless API.
- No automatic brokerage execution.

## Deployment

This repository is intended for GitHub → Vercel with the existing dedicated Supabase project.

Required server configuration is documented in `.env.example`.

The UI may load without server configuration, but analysis and persistence remain fail-closed until all required environment values are configured.
