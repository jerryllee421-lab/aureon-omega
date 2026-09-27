# AUREON Gold Data Expansion Plan

Purpose: maximize reproducible XAUUSD history available to the Evolution Engine without contaminating holdout data.

## Canonical hierarchy
1. Preserve BID + ASK M1 as the primary external market dataset.
2. Derive MID and 21 deterministic timeframes from M1.
3. Hash every canonical file and preserve date coverage/provenance.
4. Never optimize against the final holdout partition.

## Acquisition tiers
- Tier 1: 5 years rolling — fast research/control reproduction.
- Tier 2: 10 years — regime diversity.
- Tier 3: maximum available source history — archival robustness research.
- Native MT5 real ticks remain the final broker-specific authority before demo-forward promotion.

## Evolution partitions
Chronological only:
- development: oldest 60%
- validation/OOS: next 20%
- final holdout: newest 20%, sealed from mutation decisions.

## Regime labels to derive
Trend/range, volatility quartile, session, spread quartile, shock/news-proxy bars, long/short direction and calendar year.

## Storage policy
Large market data must not be committed to Git. Store compressed Parquet/cache artifacts externally with manifests and SHA-256 hashes. Repository stores only code, manifests and experiment evidence.

## Promotion rule
More data does not lower the evidence gates. A candidate that succeeds only in one year/session/regime is classified as regime-dependent rather than promoted as the universal champion.
