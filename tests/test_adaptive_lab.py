import tempfile
import unittest
from pathlib import Path
import pandas as pd
from research.evolution.run_adaptive_lab import load_bars

class AdaptiveLabLoaderTests(unittest.TestCase):
    def test_loads_canonical_bid_bars_and_hashes_source(self):
        frame = pd.DataFrame({"time":pd.date_range("2024-01-01",periods=45,freq="5min",tz="UTC"),"bid_high":[2010.0]*45,"bid_low":[1990.0]*45,"bid_close":[2000.0]*45})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bars.parquet"; frame.to_parquet(path); bars,meta=load_bars(path,"bid",100)
        self.assertEqual(len(bars),45); self.assertEqual(meta["rows"],45); self.assertEqual(len(meta["source_sha256"]),64); self.assertIn("time",bars[0])
    def test_rejects_duplicate_timestamps(self):
        frame=pd.DataFrame({"time":pd.to_datetime(["2024-01-01T00:00Z","2024-01-01T00:00Z"]),"bid_high":[2010.0]*2,"bid_low":[1990.0]*2,"bid_close":[2000.0]*2})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bars.parquet"; frame.to_parquet(path)
            with self.assertRaisesRegex(ValueError,"duplicate"): load_bars(path,"bid",100)
    def test_enforces_memory_safety_cap(self):
        frame=pd.DataFrame({"time":pd.date_range("2024-01-01",periods=3,freq="5min",tz="UTC"),"bid_high":[2010.0]*3,"bid_low":[1990.0]*3,"bid_close":[2000.0]*3})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bars.parquet"; frame.to_parquet(path)
            with self.assertRaisesRegex(ValueError,"safety cap"): load_bars(path,"bid",100 if False else 100)

if __name__ == "__main__": unittest.main()
