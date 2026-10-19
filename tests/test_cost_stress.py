import unittest

from research.evolution.cost_stress import evaluate_cost_stress


def make_bars(n=260):
    bars = []
    price = 2000.0
    for i in range(n):
        drift = 0.8 if (i // 35) % 2 == 0 else -0.65
        step = drift + (0.12 if i % 3 else -0.18)
        open_ = price
        close = price + step
        bars.append({"time": f"{i:05d}", "open": open_, "high": max(open_, close) + 0.35,
                     "low": min(open_, close) - 0.35, "close": close, "volume": 1})
        price = close
    return bars


class CostStressTests(unittest.TestCase):
    def test_cost_scenarios_return_research_only_report(self):
        result = evaluate_cost_stress(
            make_bars(300), cost_scenarios_bps=(2, 5),
            horizon_bars=3, stride=3, lookback=120, min_samples=5,
            start_index=100, end_index=270
        )
        self.assertTrue(result["research_only"])
        self.assertFalse(result["execution_authorized"])
        self.assertEqual([r["cost_bps"] for r in result["scenarios"]], [2.0, 5.0])
        self.assertIn("net_return_range", result)

    def test_invalid_cost_grid_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cost_stress(make_bars(), cost_scenarios_bps=())
        with self.assertRaises(ValueError):
            evaluate_cost_stress(make_bars(), cost_scenarios_bps=(5, 5))


if __name__ == "__main__":
    unittest.main()
