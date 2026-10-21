import unittest

import numpy as np
import pandas as pd

from research.tools.smc_intraday_candidates import build_candidates


class SMCCandidateTests(unittest.TestCase):
    def make_bars(self, n=160):
        # Deterministic structure with alternating swings and valid OHLC.
        idx = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        base = 2500 + np.sin(np.arange(n) / 4.0) * 5 + np.arange(n) * 0.025
        op = base - np.sin(np.arange(n)) * 0.5
        cl = base + np.sin(np.arange(n)) * 0.5
        hi = np.maximum(op, cl) + 0.8
        lo = np.minimum(op, cl) - 0.8
        return pd.DataFrame({"open": op, "high": hi, "low": lo, "close": cl}, index=idx)

    def test_emits_required_structure_and_setup_columns(self):
        out = build_candidates(self.make_bars())
        required = {
            "swing_high", "swing_low", "bos_up", "bos_down", "choch_up",
            "choch_down", "bullish_engulfing", "bearish_engulfing", "pinbar_up",
            "pinbar_down", "support", "resistance", "trendline_break_up",
            "trendline_break_down", "buy_side_sweep_reclaim", "sell_side_sweep_reclaim",
            "sweep_reclaim_long", "sweep_reclaim_short", "candidate_long", "candidate_short",
        }
        self.assertTrue(required.issubset(out.columns))
        self.assertEqual(len(out), 160)

    def test_pivots_are_confirmed_after_right_bars_not_backdated(self):
        idx = pd.date_range("2026-01-01", periods=9, freq="5min", tz="UTC")
        bars = pd.DataFrame({
            "open": [1, 2, 3, 4, 5, 4, 3, 2, 1],
            "high": [2, 3, 4, 5, 10, 6, 4, 3, 2],
            "low":  [0, 1, 2, 3, 4, 2, 1, 0, -1],
            "close":[1, 2, 3, 4, 8, 3, 2, 1, 0],
        }, index=idx)
        out = build_candidates(bars, left_bars=2, right_bars=2, sr_lookback=3, atr_period=2)
        self.assertTrue(np.isnan(out.swing_high.iloc[4]))
        self.assertEqual(out.swing_high.iloc[6], 10.0)

    def test_rejects_bad_ohlc(self):
        bars = self.make_bars(10)
        bars.iloc[0, bars.columns.get_loc("high")] = -999
        with self.assertRaises(ValueError):
            build_candidates(bars, left_bars=1, right_bars=1, sr_lookback=3, atr_period=2)

    def test_rejects_duplicate_timestamps(self):
        bars = self.make_bars(10)
        bars.index = [bars.index[0]] * len(bars)
        with self.assertRaises(ValueError):
            build_candidates(bars, left_bars=1, right_bars=1, sr_lookback=3, atr_period=2)


if __name__ == "__main__":
    unittest.main()
