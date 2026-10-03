import importlib.util
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("ssi", HERE/"super_scalper_intelligence.py")
SSI=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SSI)

def base(**overrides):
    data=dict(
        context_qualified=True,
        rsi_extreme=True,
        sweep_reclaim=True,
        extension_atr=2.4,
        adx=22.0,
        vol_ratio=1.10,
        minutes_from_anchor=8.0,
        m1_mss=True,
        m1_displacement_atr=0.90,
        m1_fvg_retest=True,
        m1_micro_break=True,
        m1_reclaim=True,
        gross_edge_r=0.22,
        spread_cost_r=0.03,
        slippage_cost_r=0.02,
        stale_seconds=0.5,
        latency_ms=100.0,
    )
    data.update(overrides)
    return SSI.ScalperInput(**data)

class SuperScalperIntelligenceTests(unittest.TestCase):
    def test_clean_micro_trigger_reaches_triggered(self):
        d=SSI.decide(base())
        self.assertEqual(d.state, SSI.ScalperState.TRIGGERED)
        self.assertGreaterEqual(d.readiness,82)
        self.assertGreater(d.net_edge_r,0.05)

    def test_cost_destroys_edge_and_blocks(self):
        d=SSI.decide(base(gross_edge_r=0.10,spread_cost_r=0.06,slippage_cost_r=0.04))
        self.assertEqual(d.state, SSI.ScalperState.BLOCKED)
        self.assertIn("NET_EDGE_BELOW_FLOOR",d.reasons)

    def test_good_context_without_final_micro_break_is_armed(self):
        d=SSI.decide(base(m1_micro_break=False))
        self.assertEqual(d.state, SSI.ScalperState.ARMED)

    def test_stale_data_fails_closed(self):
        d=SSI.decide(base(stale_seconds=4.0))
        self.assertEqual(d.state, SSI.ScalperState.BLOCKED)
        self.assertIn("STALE_MARKET_DATA",d.reasons)

    def test_expired_anchor_fails_closed(self):
        d=SSI.decide(base(minutes_from_anchor=61))
        self.assertEqual(d.state, SSI.ScalperState.BLOCKED)
        self.assertIn("ANCHOR_EXPIRED",d.reasons)

if __name__=="__main__":
    unittest.main()
