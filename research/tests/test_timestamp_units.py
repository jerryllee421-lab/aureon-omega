import unittest

from research.tools.timestamp_units import infer_epoch_unit


class EpochTimestampUnitTests(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(infer_epoch_unit(1_792_540_800), "s")

    def test_milliseconds(self):
        self.assertEqual(infer_epoch_unit(1_792_540_800_000), "ms")

    def test_microseconds(self):
        self.assertEqual(infer_epoch_unit(1_792_540_800_000_000), "us")

    def test_nanoseconds(self):
        self.assertEqual(infer_epoch_unit(1_792_540_800_000_000_000), "ns")

    def test_ambiguous_magnitude_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous numeric timestamp"):
            infer_epoch_unit(12_345)

    def test_non_finite_or_non_positive_fails_closed(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                infer_epoch_unit(value)


if __name__ == "__main__":
    unittest.main()
