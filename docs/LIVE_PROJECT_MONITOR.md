# AUREON PRIME Live Project Monitor

## Purpose
One mobile-first, read-only source of project truth. It automatically reflects every AUREON subsystem as evidence is produced. It is not a trading control surface.

## Connected domains
- Git/source: commit SHA, branch, build/deployment state.
- Gold Brain: acquisition coverage, rows, integrity gate, 21-TF manifest, partitions.
- Evolution: queued/running/completed experiments, verdict, rejection reason, champion/challenger metrics.
- Native validation: cTrader CLI build/backtest/tick-validation evidence when available.
- Execution: Open API approval/auth state, canary and 10-trade demo certification, reconciliation/telemetry.
- Deployment: Vercel health/version.
- Persistence: Supabase evidence ledger/status projections.
- AI: ASTRA/NVIDIA review status; advisory only.

## Truth rules
1. No artifact/evidence => UNKNOWN, never guessed.
2. RUNNING requires a fresh heartbeat.
3. Stale heartbeat => STALE, not RUNNING.
4. Test metrics must include source artifact, dataset hash and source commit.
5. AI cannot manufacture, alter or promote deterministic metrics.
6. Live-money execution remains disabled.
7. Secrets/tokens/passwords are never exposed to the monitor.

## UI
Single screen:
- overall status: RUNNING / IDLE / FAILED / BLOCKED / STALE
- current task/stage and evidence-backed progress
- Gold data coverage/integrity
- tests queued/running/completed/rejected/promoted
- frozen champion and best verified challenger
- latest verified metrics: net, PF, DD, trades, expectancy, OOS/holdout
- current blocker/error
- cTrader state
- latest commit/deployment
- last heartbeat/update time

## Integration contract
All producers publish normalized events to the Evidence Ledger. A status projector converts those events into a compact project snapshot consumed by the dashboard. The UI never scrapes logs or infers completion percentages itself.
