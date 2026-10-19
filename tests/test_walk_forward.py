import unittest

from research.evolution.walk_forward import evaluate_walk_forward
from tests.test_adaptive_prediction import make_bars


class WalkForwardTests(unittest.TestCase):
    def test_metrics_are_finite_and_research_only(self):
        result = evaluate_walk_forward(
            make_bars(420), horizon_bars=3, stride=3, lookback=150,
            min_samples=8, cost_bps=2, start_index=100, end_index=390
        )
        self.assertTrue(result["research_only"])
        self.assertFalse(result["execution_authorized"])
        self.assertGreater(result["forecast_count"], 0)
        self.assertGreaterEqual(result["coverage"], 0)
        self.assertLessEqual(result["coverage"], 1)
        self.assertGreaterEqual(result["brier_score"], 0)
        self.assertIn("regime_metrics", result)

    def test_rejects_overlapping_horizon_configuration(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(make_bars(200), horizon_bars=5, stride=1)

    def test_rejects_insufficient_range(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(make_bars(100), start_index=95, end_index=96)


if __name__ == "__main__":
    unittest.main()
