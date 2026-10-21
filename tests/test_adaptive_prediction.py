import unittest

from research.evolution.adaptive_prediction import forecast


def make_bars(n=260):
    bars = []
    price = 2000.0
    for i in range(n):
        # Deterministic alternating regimes; not intended as market-performance evidence.
        drift = 0.8 if (i // 35) % 2 == 0 else -0.65
        step = drift + (0.12 if i % 3 else -0.18)
        open_ = price
        close = price + step
        high = max(open_, close) + 0.35
        low = min(open_, close) - 0.35
        bars.append({"time": f"{i:05d}", "open": open_, "high": high,
                     "low": low, "close": close, "volume": 1})
        price = close
    return bars


class AdaptivePredictionTests(unittest.TestCase):
    def test_output_is_explicitly_research_only(self):
        result = forecast(make_bars(), horizon_bars=3, min_samples=10)
        self.assertTrue(result.research_only)
        self.assertFalse(result.execution_authorized)
        self.assertAlmostEqual(sum(result.probabilities.values()), 1.0, places=8)

    def test_future_bars_do_not_change_past_forecast(self):
        bars = make_bars()
        idx = 210
        first = forecast(bars, index=idx, horizon_bars=4, min_samples=1).to_dict()
        altered = [dict(b) for b in bars]
        for j in range(idx + 1, len(altered)):
            altered[j]["open"] *= 1.7
            altered[j]["high"] *= 1.7
            altered[j]["low"] *= 1.7
            altered[j]["close"] *= 1.7
        second = forecast(altered, index=idx, horizon_bars=4, min_samples=1).to_dict()
        self.assertEqual(first, second)

    def test_invalid_chronology_is_rejected(self):
        bars = make_bars()
        bars[100]["time"] = "00001"
        with self.assertRaises(ValueError):
            forecast(bars)

    def test_too_few_bars_rejected(self):
        with self.assertRaises(ValueError):
            forecast(make_bars(30))


if __name__ == "__main__":
    unittest.main()
