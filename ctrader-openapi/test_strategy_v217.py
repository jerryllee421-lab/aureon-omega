import unittest,sys
sys.path.insert(0,"ctrader-openapi")
from strategy_v217 import *

class V217Parity(unittest.TestCase):
 def test_bull_fvg_newest(self):
  b=[Bar(10,10.2,9.8,10,1),Bar(10,11.0,9.9,10.9,1),Bar(11,11.4,10.5,11.2,1)]
  z=newest_fvg(b); self.assertTrue(z.valid); self.assertTrue(z.bullish); self.assertEqual((z.low,z.high),(10.2,10.5))
 def test_bear_fvg(self):
  b=[Bar(11,11.2,10.8,11,1),Bar(11,11.1,10,10.1,1),Bar(10,10.5,9.6,9.9,1)]
  z=newest_fvg(b); self.assertTrue(z.valid); self.assertFalse(z.bullish); self.assertEqual((z.low,z.high),(10.5,10.8))
 def test_invalidation(self):
  self.assertTrue(closed_bar_invalidates(Zone(True,True,10,11),9.9))
  self.assertTrue(closed_bar_invalidates(Zone(True,False,10,11),11.1))
 def test_retest_buy(self):
  z=Zone(True,True,10,11)
  self.assertEqual(retest_signal(z,10.5,10.7,10.8,11,10),"BUY")
 def test_order_30r(self):
  z=Zone(True,True,100,101); p=order_plan("BUY",100.5,z,1)
  self.assertAlmostEqual(p["sl"],99.85); self.assertAlmostEqual(p["tp"],120.0)
 def test_staged_locks(self):
  entry=100; tp=130
  self.assertAlmostEqual(staged_stop("BUY",entry,tp,100.6,1),100.1)
  self.assertAlmostEqual(staged_stop("BUY",entry,tp,101.1,1),100.35)
  self.assertAlmostEqual(staged_stop("BUY",entry,tp,101.6,1),101.5)
if __name__=="__main__": unittest.main()
