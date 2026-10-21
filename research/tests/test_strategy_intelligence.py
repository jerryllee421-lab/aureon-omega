import unittest

import numpy as np
import pandas as pd

from research.tools.smc_intraday_candidates import build_candidates
from research.tools.strategy_intelligence import score_candidates


class StrategyIntelligenceTests(unittest.TestCase):
    def bars(self, n=220):
        idx = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        trend = np.linspace(2500, 2520, n) + np.sin(np.arange(n) / 4)
        op = trend - 0.2
        cl = trend + 0.2
        return pd.DataFrame({
            "open": op, "high": np.maximum(op, cl) + 0.5,
            "low": np.minimum(op, cl) - 0.5, "close": cl,
        }, index=idx)

    def test_scoring_is_auditable_and_never_authorizes_trading(self):
        features = build_candidates(self.bars())
        out = score_candidates(features)
        self.assertIn("long_score", out)
        self.assertIn("short_score", out)
        self.assertIn("decision", out)
        self.assertTrue(out.research_only.all())
        self.assertFalse(out.trade_authorized.any())

    def test_insufficient_history_abstains(self):
        out = score_candidates(build_candidates(self.bars(80)))
        self.assertTrue((out.decision == "ABSTAIN_WARMUP").all())

    def test_rejects_missing_features(self):
        f = build_candidates(self.bars()).drop(columns=["bos_up"])
        with self.assertRaises(ValueError):
            score_candidates(f)

    def test_rejects_duplicate_timestamps(self):
        f = build_candidates(self.bars())
        f.index = [f.index[0]] * len(f)
        with self.assertRaises(ValueError):
            score_candidates(f)


if __name__ == "__main__":
    unittest.main()
