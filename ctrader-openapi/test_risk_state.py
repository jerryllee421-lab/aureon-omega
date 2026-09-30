import os,tempfile,sys
sys.path.insert(0,"ctrader-openapi")
from risk_governor import *
from canary_state import *
s=BrokerSpec(100,1000,100)
assert pretrade(is_demo=True,symbol="XAUUSD",stale_seconds=1,spread_points=20,spread_limit=80,slippage_estimate=10,slippage_limit=35,margin_ok=True,daily_loss_pct=0,daily_loss_limit=3,drawdown_pct=0,drawdown_limit=6,has_stop=True,volume=100,spec=s,open_positions=0,completed=0).ok
assert pretrade(is_demo=False,symbol="XAUUSD",stale_seconds=1,spread_points=20,spread_limit=80,slippage_estimate=10,slippage_limit=35,margin_ok=True,daily_loss_pct=0,daily_loss_limit=3,drawdown_pct=0,drawdown_limit=6,has_stop=True,volume=100,spec=s,open_positions=0,completed=0).reason=="LIVE_BLOCK"
assert pretrade(is_demo=True,symbol="XAUUSD",stale_seconds=1,spread_points=20,spread_limit=80,slippage_estimate=10,slippage_limit=35,margin_ok=True,daily_loss_pct=0,daily_loss_limit=3,drawdown_pct=0,drawdown_limit=6,has_stop=True,volume=100,spec=s,open_positions=0,completed=5).reason=="CANARY_LIMIT"
with tempfile.TemporaryDirectory() as d:
 st=StateStore(os.path.join(d,"s.json"),os.path.join(d,"e.jsonl"),5)
 x=st.load();x.open_position_id="1";st.save(x)
 y=st.reconcile([]);assert y.halted and y.halt_reason=="STATE_MISMATCH"
print("risk/state PASS")
