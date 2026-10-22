import unittest

import pandas as pd

from research.tools.quote_execution import simulate_quote_exit


def quotes(times, bids, asks):
    return pd.DataFrame({
        "timestamp": pd.to_datetime(times, utc=True),
        "bid": bids,
        "ask": asks,
    })


class QuoteExecutionTests(unittest.TestCase):
    def test_long_enters_ask_and_exits_bid_on_target_quote(self):
        ticks = quotes(
            ["2026-10-21T10:00:01Z", "2026-10-21T10:00:02Z"],
            [100.0, 101.2], [100.2, 101.4]
        )
        r = simulate_quote_exit(ticks, "2026-10-21T10:00:00Z", 1, 99.0, 101.0,
                                slippage_price_units=0)
        self.assertEqual(r.status, "CLOSED")
        self.assertEqual(r.reason, "TP")
        self.assertAlmostEqual(r.entry_price, 100.2)
        self.assertAlmostEqual(r.exit_price, 101.2)

    def test_short_enters_bid_and_exits_ask_on_stop(self):
        ticks = quotes(
            ["2026-10-21T10:00:01Z", "2026-10-21T10:00:02Z"],
            [100.0, 101.0], [100.2, 101.2]
        )
        r = simulate_quote_exit(ticks, "2026-10-21T10:00:00Z", -1, 101.0, 98.0,
                                slippage_price_units=0.3)
        self.assertEqual(r.reason, "SL")
        self.assertAlmostEqual(r.entry_price, 100.0)
        self.assertAlmostEqual(r.exit_price, 101.5)

    def test_rejects_wide_spread_and_stale_entry(self):
        wide = quotes(["2026-10-21T10:00:01Z"], [100.0], [101.0])
        r = simulate_quote_exit(wide, "2026-10-21T10:00:00Z", 1, 99, 102)
        self.assertEqual(r.status, "REJECTED_WIDE_SPREAD")
        stale = quotes(["2026-10-21T10:02:00Z"], [100.0], [100.2])
        r = simulate_quote_exit(stale, "2026-10-21T10:00:00Z", 1, 99, 102)
        self.assertEqual(r.status, "REJECTED_STALE_ENTRY")

    def test_gap_is_not_silently_treated_as_normal_execution(self):
        ticks = quotes(
            ["2026-10-21T10:00:01Z", "2026-10-21T10:02:00Z"],
            [100.0, 100.5], [100.2, 100.7]
        )
        r = simulate_quote_exit(ticks, "2026-10-21T10:00:00Z", 1, 99, 102,
                                max_quote_gap_seconds=30)
        self.assertEqual(r.status, "GAP_MARK")
        self.assertEqual(r.reason, "QUOTE_GAP")

    def test_no_exit_is_marked_not_counted_as_closed(self):
        ticks = quotes(
            ["2026-10-21T10:00:01Z", "2026-10-21T10:00:02Z"],
            [100.0, 100.1], [100.2, 100.3]
        )
        r = simulate_quote_exit(ticks, "2026-10-21T10:00:00Z", 1, 98, 105)
        self.assertEqual(r.status, "END_OF_DATA_MARK")
        self.assertEqual(r.reason, "END_OF_DATA_MARK")


if __name__ == "__main__":
    unittest.main()
