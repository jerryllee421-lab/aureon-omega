"""Fail-closed pre-trade Risk Governor."""
from dataclasses import dataclass
@dataclass(frozen=True)
class BrokerSpec:
    min_volume:int; max_volume:int; step_volume:int
@dataclass(frozen=True)
class Gate:
    ok:bool; reason:str
def volume_valid(v,s):
    return s.min_volume<=v<=s.max_volume and (v-s.min_volume)%s.step_volume==0
def pretrade(*,is_demo,symbol,stale_seconds,spread_points,spread_limit,slippage_estimate,slippage_limit,
             margin_ok,daily_loss_pct,daily_loss_limit,drawdown_pct,drawdown_limit,has_stop,volume,spec,
             open_positions,completed,canary_limit=5):
    checks=[
      (is_demo,"LIVE_BLOCK"),(symbol.upper().startswith("XAU"),"NON_XAU"),
      (stale_seconds<=3,"STALE_DATA"),(spread_points<=spread_limit,"SPREAD"),
      (slippage_estimate<=slippage_limit,"SLIPPAGE"),(margin_ok,"MARGIN"),
      (daily_loss_pct<daily_loss_limit,"DAILY_LOSS"),(drawdown_pct<drawdown_limit,"DRAWDOWN"),
      (has_stop,"NO_STOP"),(volume_valid(volume,spec),"VOLUME"),(open_positions==0,"POSITION_EXISTS"),
      (completed<canary_limit,"CANARY_LIMIT")]
    for ok,reason in checks:
        if not ok:return Gate(False,reason)
    return Gate(True,"PASS")
