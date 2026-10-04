import csv,importlib.util,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("importer",HERE/"import_mt5_forensics.py")
MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)
def write_csv(path,headers,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=headers,delimiter=";"); w.writeheader(); w.writerows(rows)
class ImporterTests(unittest.TestCase):
    def test_candidate_selected_on_validation_not_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            sh=["research_id","gold_symbol","variant_id","variant","portfolio_trades","profit_factor","portfolio_expectancy_R","net_R","max_dd_R","event_fast_n","event_fast_expectancy_R","event_slow_n","event_slow_expectancy_R"]
            write_csv(root/MOD.SUMMARY_NAME,sh,[
              dict(zip(sh,[1,"XAUUSD",0,"CONTROL",100,1.2,.10,10,5,100,.08,100,.07])),
              dict(zip(sh,[1,"XAUUSD",1,"A",80,1.4,.20,16,5,80,.15,80,.12])),
              dict(zip(sh,[1,"XAUUSD",2,"B",90,1.3,.18,16.2,5,90,.14,90,.11]))])
            ph=["research_id","period_or_fold","variant_id","variant","trades","wins","losses","win_rate","profit_factor","portfolio_expectancy_R","net_R","max_dd_R","event_fast_n","event_fast_expectancy_R","event_slow_n","event_slow_expectancy_R"]
            write_csv(root/MOD.PERIOD_NAME,ph,[
              dict(zip(ph,[1,"FOLD_VALIDATION",1,"A",30,18,12,.6,1.5,.25,7.5,3,30,.2,30,.18])),
              dict(zip(ph,[1,"FOLD_VALIDATION",2,"B",30,18,12,.6,1.2,.15,4.5,3,30,.1,30,.09])),
              dict(zip(ph,[1,"FOLD_HOLDOUT",1,"A",25,13,12,.52,1.1,.05,1.25,4,25,.04,25,.03])),
              dict(zip(ph,[1,"FOLD_HOLDOUT",2,"B",25,20,5,.8,3.0,.80,20,2,25,.7,25,.6])),
              dict(zip(ph,[1,"2026-H1",1,"A",20,11,9,.55,1.1,.04,.8,2,20,.03,20,.02]))])
            report=MOD.build_report(root)
            self.assertEqual(report["selected_candidate"],"A")
            self.assertEqual(report["candidate_id"],1)
            self.assertEqual(report["holdout_status"],"PASS")
    def test_control_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            sh=["variant_id","variant","portfolio_trades","profit_factor","portfolio_expectancy_R","net_R","max_dd_R"]
            write_csv(root/MOD.SUMMARY_NAME,sh,[dict(zip(sh,[1,"A",10,1.2,.1,1,1]))])
            ph=["period_or_fold","variant_id","variant","trades","profit_factor","portfolio_expectancy_R","net_R","max_dd_R"]
            write_csv(root/MOD.PERIOD_NAME,ph,[dict(zip(ph,["FOLD_VALIDATION",1,"A",10,1.2,.1,1,1]))])
            with self.assertRaises(ValueError): MOD.build_report(root)
if __name__=="__main__": unittest.main()
