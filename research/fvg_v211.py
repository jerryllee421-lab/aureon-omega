from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
import numpy as np
import pandas as pd

@dataclass
class Params:
    min_fvg_atr: float=.15
    min_body_atr: float=.50
    min_body_ratio: float=.60
    max_fvg_bars: int=1000
    replace_with_new_fvg: bool=True
    one_trade_per_fvg: bool=True
    use_bias_filter: bool=False
    bias_fast_ema: int=20
    bias_slow_ema: int=50
    require_midpoint: bool=False
    require_rejection: bool=True
    reward_risk: float=30.0
    max_sl_atr: float=3.0
    atr_period: int=14
    sl_atr_buffer: float=.15
    use_profit_lock: bool=True
    lock1_trigger_rr: float=.50
    lock1_rr: float=.10
    lock2_trigger_rr: float=1.0
    lock2_rr: float=.35
    trail_start_rr: float=1.5
    trail_atr: float=.10
    max_spread_price: float=1.0
    max_trades_day: int=1000

@dataclass
class Zone:
    bullish: bool
    low: float
    high: float
    formed_i: int
    traded: bool=False

@dataclass
class Trade:
    entry_i:int; exit_i:int; bullish:bool; entry:float; stop:float; target:float; exit:float; r:float; reason:str


def _atr(df:pd.DataFrame,n:int)->pd.Series:
    prev=df.mid_close.shift(1)
    tr=pd.concat([(df.mid_high-df.mid_low).abs(),(df.mid_high-prev).abs(),(df.mid_low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def _metrics(trades:list[Trade])->dict:
    rs=np.array([t.r for t in trades],dtype=float)
    if len(rs)==0: return {"trades":0,"win_rate":0.0,"expectancy_r":0.0,"profit_factor":0.0,"max_drawdown_r":0.0,"net_r":0.0,"sharpe_r":0.0}
    wins=rs[rs>0].sum(); losses=-rs[rs<0].sum(); eq=np.r_[0,rs.cumsum()]; peak=np.maximum.accumulate(eq); dd=peak-eq
    return {
      "trades":int(len(rs)),"win_rate":float((rs>0).mean()),"expectancy_r":float(rs.mean()),
      "profit_factor":float(wins/losses) if losses>0 else (999.0 if wins>0 else 0.0),
      "max_drawdown_r":float(dd.max()),"net_r":float(rs.sum()),
      "sharpe_r":float(rs.mean()/rs.std(ddof=1)*sqrt(len(rs))) if len(rs)>1 and rs.std(ddof=1)>0 else 0.0,
      "median_r":float(np.median(rs)),"max_loss_streak":_max_loss_streak(rs)
    }


def _max_loss_streak(rs):
    best=cur=0
    for r in rs:
        cur=cur+1 if r<0 else 0; best=max(best,cur)
    return int(best)


def run(df:pd.DataFrame,p:Params)->tuple[list[Trade],dict]:
    x=df.reset_index(drop=True).copy()
    x["atr"]=_atr(x,p.atr_period)
    x["fast"]=x.mid_close.ewm(span=p.bias_fast_ema,adjust=False).mean()
    x["slow"]=x.mid_close.ewm(span=p.bias_slow_ema,adjust=False).mean()
    zone=None; pos=None; trades=[]; day=None; trades_day=0

    for i in range(max(p.atr_period+3,3),len(x)):
        row=x.iloc[i]; current_day=pd.Timestamp(row.time).date()
        if current_day!=day: day=current_day; trades_day=0

        # Manage open position conservatively using bar extremes. If stop and TP are both touched, stop wins.
        if pos is not None:
            bull=pos["bull"]; stop=pos["stop"]; target=pos["target"]; entry=pos["entry"]; risk=pos["risk"]
            stop_hit = row.bid_low<=stop if bull else row.ask_high>=stop
            tp_hit = row.bid_high>=target if bull else row.ask_low<=target
            if stop_hit or tp_hit:
                exit_px=stop if stop_hit else target; rr=(exit_px-entry)/risk if bull else (entry-exit_px)/risk
                trades.append(Trade(pos["entry_i"],i,bull,entry,pos["initial_stop"],target,exit_px,float(rr),"SL" if stop_hit else "TP")); pos=None
            else:
                mark=row.bid_close if bull else row.ask_close
                rr=(mark-entry)/risk if bull else (entry-mark)/risk
                new_stop=stop
                if p.use_profit_lock:
                    lock=-1
                    if rr>=p.lock2_trigger_rr: lock=p.lock2_rr
                    elif rr>=p.lock1_trigger_rr: lock=p.lock1_rr
                    if lock>=0: new_stop=max(new_stop,entry+risk*lock) if bull else min(new_stop,entry-risk*lock)
                if rr>=p.trail_start_rr and row.atr>0:
                    trail=mark-row.atr*p.trail_atr if bull else mark+row.atr*p.trail_atr
                    floor=entry+risk*p.lock2_rr if bull else entry-risk*p.lock2_rr
                    trail=max(trail,floor) if bull else min(trail,floor)
                    new_stop=max(new_stop,trail) if bull else min(new_stop,trail)
                pos["stop"]=new_stop
            if pos is not None: continue

        # Find newest FVG using three closed bars ending at i-1: old=i-3, middle=i-2, new=i-1.
        old=x.iloc[i-3]; mid=x.iloc[i-2]; new=x.iloc[i-1]; a=mid.atr
        if np.isfinite(a) and a>0:
            body=abs(mid.mid_close-mid.mid_open); rng=mid.mid_high-mid.mid_low
            candidate=None
            if body>=a*p.min_body_atr and rng>0 and body/rng>=p.min_body_ratio:
                if old.mid_high<new.mid_low and mid.mid_close>mid.mid_open and (new.mid_low-old.mid_high)>=a*p.min_fvg_atr:
                    candidate=Zone(True,float(old.mid_high),float(new.mid_low),i-1)
                elif old.mid_low>new.mid_high and mid.mid_close<mid.mid_open and (old.mid_low-new.mid_high)>=a*p.min_fvg_atr:
                    candidate=Zone(False,float(new.mid_high),float(old.mid_low),i-1)
            if candidate and (zone is None or p.replace_with_new_fvg): zone=candidate

        if zone is None or i-zone.formed_i>p.max_fvg_bars or (p.one_trade_per_fvg and zone.traded) or trades_day>=p.max_trades_day: continue
        # Invalidation uses previous close in the EA; proxy with latest completed mid close.
        prev=x.iloc[i-1]
        if (zone.bullish and prev.mid_close<zone.low) or ((not zone.bullish) and prev.mid_close>zone.high): zone=None; continue
        if row.spread_close>p.max_spread_price: continue
        if p.use_bias_filter:
            if zone.bullish and not (prev.fast>prev.slow): continue
            if not zone.bullish and not (prev.fast<prev.slow): continue

        midpoint=(zone.low+zone.high)/2
        price=row.ask_close if zone.bullish else row.bid_close
        inside=zone.low<=price<=zone.high
        if not inside: continue
        if p.require_midpoint and ((zone.bullish and price>midpoint) or ((not zone.bullish) and price<midpoint)): continue
        rng=row.mid_high-row.mid_low
        if p.require_rejection:
            if rng<=0: continue
            close_pos=(row.mid_close-row.mid_low)/rng
            if zone.bullish and close_pos<.55: continue
            if (not zone.bullish) and close_pos>.45: continue
        a=row.atr
        if not np.isfinite(a) or a<=0: continue
        if zone.bullish:
            sl=zone.low-a*p.sl_atr_buffer; risk=price-sl
            if risk<=0 or risk>a*p.max_sl_atr: continue
            tp=price+risk*p.reward_risk
        else:
            sl=zone.high+a*p.sl_atr_buffer; risk=sl-price
            if risk<=0 or risk>a*p.max_sl_atr: continue
            tp=price-risk*p.reward_risk
        pos={"bull":zone.bullish,"entry":float(price),"stop":float(sl),"initial_stop":float(sl),"target":float(tp),"risk":float(risk),"entry_i":i}
        zone.traded=True; trades_day+=1

    if pos is not None:
        row=x.iloc[-1]; exit_px=row.bid_close if pos["bull"] else row.ask_close; rr=(exit_px-pos["entry"])/pos["risk"] if pos["bull"] else (pos["entry"]-exit_px)/pos["risk"]
        trades.append(Trade(pos["entry_i"],len(x)-1,pos["bull"],pos["entry"],pos["initial_stop"],pos["target"],float(exit_px),float(rr),"EOD"))
    return trades,_metrics(trades)


def trades_frame(trades:list[Trade])->pd.DataFrame:
    return pd.DataFrame([asdict(t) for t in trades])
