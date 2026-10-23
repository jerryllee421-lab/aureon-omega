"""Regression tests for split boundaries and validation-only candidate selection."""
import unittest
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_research import split, select_validation_winner


class ResearchSplitTests(unittest.TestCase):
    def test_splits_are_disjoint_chronological_and_cover_rows(self):
        df = pd.DataFrame({
            "time": pd.date_range("2025-01-01", periods=100, freq="min"),
            "close": range(100),
        })
        dev, val, hold = split(df, {"development": 0.6, "validation": 0.2, "holdout": 0.2})
        self.assertEqual((len(dev), len(val), len(hold)), (60, 20, 20))
        self.assertLess(dev.time.max(), val.time.min())
        self.assertLess(val.time.max(), hold.time.min())
        self.assertEqual(pd.concat([dev, val, hold]).close.tolist(), list(range(100)))

    def test_custom_valid_split_fractions_are_respected(self):
        df = pd.DataFrame({"time": pd.date_range("2025-01-01", periods=10, freq="min")})
        dev, val, hold = split(df, {"development": 0.5, "validation": 0.3, "holdout": 0.2})
        self.assertEqual([len(dev), len(val), len(hold)], [5, 3, 2])

    def test_candidate_selection_uses_validation_not_holdout(self):
        candidates = [
            {"candidate": 1, "validation": {"score": 2.0}, "holdout": {"score": 999.0}},
            {"candidate": 2, "validation": {"score": 3.0}, "holdout": {"score": -999.0}},
        ]
        self.assertEqual(select_validation_winner(candidates)["candidate"], 2)

    def test_empty_candidate_list_has_no_winner(self):
        self.assertIsNone(select_validation_winner([]))

    def test_unqualified_validation_candidates_do_not_reach_holdout(self):
        candidates = [
            {"candidate": 1, "validation": {"score": -1e9}},
            {"candidate": 2, "validation": {"score": -1e9}},
        ]
        self.assertIsNone(select_validation_winner(candidates))


if __name__ == "__main__":
    unittest.main()
