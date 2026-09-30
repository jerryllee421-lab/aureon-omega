"""Pure deterministic V2.17 signal core for Open API parity tests.
No networking, credentials, or broker writes live here.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Bar:
    o: float; h: float; l: float; c: float; atr: float

@dataclass
class Zone:
    valid: bool=False
    bullish: bool=False
    low: float=0.0
    high: float=0.0
    traded: bool=False

def newest_fvg(bars, min_fvg_atr=.15, min_body_atr=.50, min_body_ratio=.60, lookback=1000):
    """Mirrors AUREONPrimeGoldCloud.UpdateZoneOnNewBar: newest valid 3-candle FVG wins."""
    if len(bars)<3: return Zone()
    closed=len(bars)-1
    oldest=max(2,closed-lookback)
    for i in range(closed,oldest-1,-1):
        middle=i-1; old=i-2
        atr=bars[i].atr
        if atr<=0: continue
        body=abs(bars[middle].c-bars[middle].o)
        rng=bars[middle].h-bars[middle].l
        if rng<=0 or body<atr*min_body_atr or body/rng<min_body_ratio: continue
        bull=bars[old].h<bars[i].l and bars[middle].c>bars[middle].o
        bear=bars[old].l>bars[i].h and bars[middle].c<bars[middle].o
        gap=(bars[i].l-bars[old].h) if bull else ((bars[old].l-bars[i].h) if bear else 0)
        if (not bull and not bear) or gap<atr*min_fvg_atr: continue
        return Zone(True,bull,bars[old].h if bull else bars[i].h,
                    bars[i].l if bull else bars[old].l,False)
    return Zone()

def closed_bar_invalidates(z:Zone,last_closed:float)->bool:
    return z.valid and ((z.bullish and last_closed<z.low) or ((not z.bullish) and last_closed>z.high))

def current_bar_rejection(bullish:bool, high:float, low:float, bid:float, ask:float)->bool:
    rng=high-low
    if rng<=0:return False
    px=bid if bullish else ask
    pos=(px-low)/rng
    return pos>=.55 if bullish else pos<=.45

def retest_signal(z:Zone,last_closed:float,bid:float,ask:float,current_high:float,current_low:float,
                  one_trade_per_fvg=False,allow_long=True,allow_short=True)->Optional[str]:
    if not z.valid or closed_bar_invalidates(z,last_closed): return None
    px=ask if z.bullish else bid
    if px<z.low or px>z.high:return None
    if not current_bar_rejection(z.bullish,current_high,current_low,bid,ask):return None
    if one_trade_per_fvg and z.traded:return None
    if z.bullish and allow_long:return "BUY"
    if (not z.bullish) and allow_short:return "SELL"
    return None

def order_plan(side,entry,zone,atr,sl_atr_buffer=.15,max_sl_atr=3.0,reward_risk=30.0):
    edge=zone.low if side=="BUY" else zone.high
    sl=edge-atr*sl_atr_buffer if side=="BUY" else edge+atr*sl_atr_buffer
    risk=abs(entry-sl)
    if risk<=0 or risk>atr*max_sl_atr:return None
    tp=entry+risk*reward_risk if side=="BUY" else entry-risk*reward_risk
    return {"side":side,"entry":entry,"sl":sl,"tp":tp,"risk_price":risk}

def staged_stop(side,entry,tp,current,atr,reward_risk=30.0):
    risk=abs(tp-entry)/reward_risk
    if risk<=0:return None
    rr=((current-entry) if side=="BUY" else (entry-current))/risk
    if rr<=0:return None
    cand=None
    if rr>=1.0:cand=entry+risk*.35 if side=="BUY" else entry-risk*.35
    elif rr>=.5:cand=entry+risk*.10 if side=="BUY" else entry-risk*.10
    if rr>=1.5:
        t=current-atr*.10 if side=="BUY" else current+atr*.10
        floor=entry+risk*.35 if side=="BUY" else entry-risk*.35
        t=max(t,floor) if side=="BUY" else min(t,floor)
        cand=t if cand is None else (max(cand,t) if side=="BUY" else min(cand,t))
    return cand
