import unittest
import numpy as np
import pandas as pd
from research.tools.smc_variant_evaluation import evaluate, _metrics

class SMCVariantEvaluationTests(unittest.TestCase):
    def bars(self,n=500):
        idx=pd.date_range("2026-01-01",periods=n,freq="5min",tz="UTC")
        t=np.arange(n)
        close=2500 + 0.025*t + 2*np.sin(t/5)
        op=close-0.15*np.cos(t/3)
        return pd.DataFrame({"open":op,"high":np.maximum(op,close)+0.5,
          "low":np.minimum(op,close)-0.5,"close":close},index=idx)
    def test_all_variants_report_oos_and_cost_model(self):
        r=evaluate(self.bars())
        self.assertEqual(r["bars"],500)
        self.assertIn("not tick execution",r["cost_model"])
        self.assertEqual(len(r["variants"]),8)
        for v in r["variants"].values():
            self.assertIn("out_of_sample",v)
            self.assertIn("profit_factor",v["all"])
    def test_costs_reduce_net_result(self):
        cheap=evaluate(self.bars(),spread_cost=0,slippage=0)
        costly=evaluate(self.bars(),spread_cost=2,slippage=1)
        for name in cheap["variants"]:
            self.assertLessEqual(costly["variants"][name]["all"]["net_price_units"],
                                 cheap["variants"][name]["all"]["net_price_units"])
    def test_metrics_empty_sample(self):
        m=_metrics([])
        self.assertEqual(m["trades"],0)
        self.assertIsNone(m["expectancy_price_units"])
if __name__=="__main__": unittest.main()
