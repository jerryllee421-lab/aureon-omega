# AUREON Ω verification record — 2026-09-28

## Repository / application verification

- GitHub repository is public and `main` is the production authority.
- Standard CI passes Node install, automated tests, production build, and research-Python syntax validation.
- The latest integration preview deployment completed successfully on Vercel.
- Production deployment is in Vercel `READY` state and no runtime errors were reported in the checked seven-day window.
- Public anonymous calls to `/api/health` and `/api/status` are redirected by Vercel SSO; therefore anonymous health probing is not a valid readiness test for the current protected deployment.
- Supabase project is `ACTIVE_HEALTHY`; the AUREON service Edge Function is active.
- Owner-scoped RLS policies use cached `(select auth.uid())` / `(select auth.jwt())` forms. Project-monitor tables remain fail-closed/server-only.

## Gold research verification

- The immutable XAUUSD history mirror and pinned end date are configured in the Gold research workflow.
- The active reference run successfully completed XAUUSD M1 bid/ask import and integrity validation across all 21 standard timeframes before entering candidate evaluation.
- V2.12 is now the frozen historical control with exact source, exact tester preset and machine-readable benchmark metadata.
- The Python evaluator is explicitly a research proxy, not an MT5 tick-equivalent engine.
- Candidate evaluation now reuses invariant ATR/EMA calculations and samples the entire Cartesian parameter space deterministically instead of taking a biased lexicographic prefix.
- Future canonical Gold research runs use the V2.12 control profile.

## EA lineage

- Frozen control: `ea/baseline/FVG_Scalper_V2_12_Research.mq5`.
- Primary MT5 challenger: `ea/challengers/FVG_Scalper_V4_00_ASTRA_ResearchAccelerator_AllInOne.mq5`.
- ASTRA Campaign V1 assets are preserved under `ea/challengers/astra-campaign-v1/`.
- cTrader Cloud is a demo-only parity/certification lane. The cBot hard-stops on live accounts.

## External certification still required

These are native-platform evidence gates, not repository-development tasks:

1. Compile V2.12/V4 in MetaEditor and execute MT5 Strategy Tester on broker real ticks.
2. Run untouched out-of-sample, walk-forward and execution-cost stress campaigns.
3. Compile the cTrader cBot natively and perform cTrader historical parity testing.
4. Validate persistence/restart and order/fill/position/close reconciliation on a cTrader demo account.
5. Complete controlled demo-forward validation before any live-risk release is considered.

No historical backtest result is treated as a forecast or guarantee.
