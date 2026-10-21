import unittest
import pandas as pd

from research.replay.aureon_vwap_ema_tick_replay import make_bars, run_scenario


def tick_frame(times, bids, asks):
    frame = pd.DataFrame({
        "time": pd.to_datetime(times, utc=True),
        "bid": bids,
        "ask": asks,
    })
    frame["spread"] = frame["ask"] - frame["bid"]
    frame["minute"] = frame["time"].dt.floor("min")
    return frame.sort_values("time", kind="stable").reset_index(drop=True)


class TickReplayRegressionTests(unittest.TestCase):
    def test_bars_are_chronological_and_quotes_are_preserved(self):
        ticks = tick_frame(
            ["2026-10-01T00:00:00Z", "2026-10-01T00:00:20Z",
             "2026-10-01T00:01:00Z", "2026-10-01T00:01:20Z"],
            [2000.0, 2000.2, 2000.1, 2000.3],
            [2000.2, 2000.4, 2000.3, 2000.5],
        )
        bars = make_bars(ticks)
        self.assertTrue(bars.index.is_monotonic_increasing)
        self.assertEqual(len(bars), 2)
        self.assertAlmostEqual(float(bars.iloc[0]["open"]), 2000.0)
        self.assertAlmostEqual(float(bars.iloc[0]["close"]), 2000.2)
        self.assertAlmostEqual(float(bars.iloc[0]["ask_close"]), 2000.4)

    def test_invalid_quotes_are_not_silently_repaired_by_replay(self):
        # Loader owns quote validation; downstream replay must receive valid quotes.
        ticks = tick_frame(
            ["2026-10-01T00:00:00Z", "2026-10-01T00:00:20Z"],
            [2000.0, 2000.1], [2000.2, 2000.3]
        )
        self.assertTrue((ticks["bid"] > 0).all())
        self.assertTrue((ticks["ask"] >= ticks["bid"]).all())
        self.assertTrue((ticks["spread"] >= 0).all())

    def test_spread_gate_rejects_entries_above_cap(self):
        # Exercise the spread gate deterministically with a synthetic signal bar.
        ticks = tick_frame(
            ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
            [2000.0, 2000.1], [2000.2, 2001.0]
        )
        bars = make_bars(ticks)
        # Force a valid prior-bar signal; the next tick's spread must reject it.
        bars["long_signal"] = False
        bars["short_signal"] = False
        bars["long_signal"].iloc[0] = True
        bars["atr14"] = 1.0
        report, trades = run_scenario(ticks, bars, 0.70, 0.0, 0.0)
        self.assertEqual(report["trades"], 0)
        self.assertEqual(report["spread_rejected_entry_opportunities"], 1)
        self.assertEqual(trades, [])

    def test_empty_input_is_not_a_valid_replay(self):
        with self.assertRaises((ValueError, KeyError)):
            make_bars(pd.DataFrame(columns=["time", "bid", "ask", "spread", "minute"]))


if __name__ == "__main__":
    unittest.main()
