import os
import unittest
from unittest.mock import patch

import pandas as pd

from research.tools.offline_tick_replay import parse_timestamp, decode_bi5


class TimestampParsingTests(unittest.TestCase):
    def test_epoch_seconds_are_not_interpreted_as_nanoseconds(self):
        parsed = parse_timestamp(pd.Series([1792540800]), "timestamp")
        self.assertEqual(parsed.iloc[0], pd.Timestamp("2026-10-21T00:00:00Z"))

    def test_epoch_milliseconds_are_parsed(self):
        parsed = parse_timestamp(pd.Series([1792540800000]), "timestamp")
        self.assertEqual(parsed.iloc[0], pd.Timestamp("2026-10-21T00:00:00Z"))

    def test_explicit_millisecond_column_is_parsed(self):
        parsed = parse_timestamp(pd.Series([1792540800000]), "time_msc")
        self.assertEqual(parsed.iloc[0], pd.Timestamp("2026-10-21T00:00:00Z"))

    def test_ambiguous_small_numeric_timestamp_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous numeric timestamp"):
            parse_timestamp(pd.Series([12345]), "timestamp")

    def test_bi5_requires_explicit_verified_price_scale(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "BI5 price scale is instrument-specific"):
                decode_bi5(b"not-used", "2026/10/21/00h_ticks.bi5")


if __name__ == "__main__":
    unittest.main()
