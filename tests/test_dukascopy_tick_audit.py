"""Tests for the third-party XAUUSD tick archive quality gate."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from research.evolution.audit_dukascopy_tick_archive import audit
from research.evolution.convert_dukascopy_ticks_to_mt5_csv import convert


class DukascopyTickAuditTests(unittest.TestCase):
    def write_ticks(self, root: Path, times, bids, asks):
        target = root / "tick" / "Forex" / "Metals" / "XAU-USD"
        target.mkdir(parents=True)
        table = pa.table({
            "time": pa.array(times, type=pa.timestamp("ms", tz="UTC")),
            "bid": pa.array(bids, type=pa.float64()),
            "ask": pa.array(asks, type=pa.float64()),
            "bid_volume": pa.array([1.0] * len(times)),
            "ask_volume": pa.array([1.0] * len(times)),
        })
        pq.write_table(table, target / "2026-01-01.parquet", row_group_size=2)

    def test_valid_sorted_ticks_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            times = [
                datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
            ]
            self.write_ticks(root, times, [2000.0, 2000.1, 2000.2], [2000.2, 2000.3, 2000.4])
            report = audit(root, batch_size=2)
            self.assertEqual(report["quality_gate"], "PASS")
            self.assertEqual(report["tick_count"], 3)
            self.assertEqual(report["out_of_order_count"], 0)

    def test_mt5_conversion_requires_clean_audit_and_preserves_tick_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            out = Path(temp) / "mt5"
            root.mkdir()
            times = [
                datetime(2026, 1, 1, 0, 0, 0, 123000, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 0, 0, 1, 456000, tzinfo=timezone.utc),
            ]
            self.write_ticks(root, times, [2000.0, 2000.1], [2000.2, 2000.3])
            report = convert(root, out, batch_size=1)
            self.assertEqual(report["input_quality_gate"], "PASS")
            self.assertEqual(report["input_tick_count"], report["output_tick_count"])
            with (out / "XAUUSD-2026-01-01.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0:2], ["2026.01.01", "00:00:00.123"])
            self.assertEqual(rows[0][6], "6")
            manifest = json.loads((out / "MT5_IMPORT_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["output_tick_count"], 2)

    def test_bad_quotes_and_order_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            times = [
                datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 0, 0, 3, tzinfo=timezone.utc),
            ]
            self.write_ticks(root, times, [2000.0, 0.0, 2000.2], [1999.0, 2000.1, 2000.4])
            report = audit(root, batch_size=2)
            self.assertEqual(report["quality_gate"], "FAIL")
            self.assertEqual(report["out_of_order_count"], 1)
            self.assertEqual(report["nonpositive_bid_count"], 1)
            self.assertEqual(report["ask_below_bid_count"], 1)


if __name__ == "__main__":
    unittest.main()
