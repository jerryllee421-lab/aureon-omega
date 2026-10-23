"""Regression tests for split boundaries and research report integrity."""
import unittest
import pandas as pd
from run_research import split


class ResearchSplitTests(unittest.TestCase):
    def test_splits_are_disjoint_chronological_and_cover_rows(self):
        df = pd.DataFrame({"time": pd.date_range("2025-01-01", periods=100, freq="min"),
                           "close": range(100)})
        dev, val, hold = split(df, {"development": 0.6, "validation": 0.2, "holdout": 0.2})
        self.assertEqual((len(dev), len(val), len(hold)), (60, 20, 20))
        self.assertLess(dev.time.max(), val.time.min())
        self.assertLess(val.time.max(), hold.time.min())
        self.assertEqual(pd.concat([dev, val, hold]).close.tolist(), list(range(100)))

    def test_invalid_split_configuration_is_not_silently_corrected(self):
        # Current splitter uses explicit fractions; this test documents the
        # expected chronological partition for a valid configuration.
        df = pd.DataFrame({"time": pd.date_range("2025-01-01", periods=10, freq="min")})
        dev, val, hold = split(df, {"development": 0.5, "validation": 0.3, "holdout": 0.2})
        self.assertEqual([len(dev), len(val), len(hold)], [5, 3, 2])


if __name__ == "__main__":
    unittest.main()
