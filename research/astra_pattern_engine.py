from __future__ import annotations

"""Deterministic candlestick + chart-pattern knowledge for ASTRA Market Brain.

Patterns are evidence, never standalone trade authority. All labels are causal:
only the current and already-closed bars are used. A pivot is considered
confirmed only after the next closed bar exists.

The engine deliberately prefers a smaller set of mechanically definable
patterns over subjective visual pattern matching.
"""

import math
import numpy as np
import pandas as pd


def _line_slope(values: np.ndarray) -> float:
    if len(values) < 2 or not np.isfinite(values).all():
        return 0.0
    x=np.arange(len(values),dtype=float)
    return float(np.polyfit(x,values.astype(float),1)[0])


def _safe(v, default=0.0) -> float:
    try:
        f=float(v)
        return f if math.isfinite(f) else default
    except Exception:
        return default


def annotate_candlesticks(x: pd.DataFrame) -> pd.DataFrame:
    y=x.copy()
    body=(y["mid_close"]-y["mid_open"]).abs()
    rng=(y["mid_high"]-y["mid_low"]).replace(0,np.nan)
    upper=y["mid_high"]-y[["mid_open","mid_close"]].max(axis=1)
    lower=y[["mid_open","mid_close"]].min(axis=1)-y["mid_low"]
    body_pct=(body/rng).fillna(0.0)
    upper_pct=(upper/rng).fillna(0.0)
    lower_pct=(lower/rng).fillna(0.0)
    atr=y["atr14"].replace(0,np.nan)

    prev_open=y["mid_open"].shift(1)
    prev_close=y["mid_close"].shift(1)
    prev_body=(prev_close-prev_open).abs()

    bull=y["mid_close"]>y["mid_open"]
    bear=y["mid_close"]<y["mid_open"]
    prev_bull=prev_close>prev_open
    prev_bear=prev_close<prev_open

    bull_engulf=(
        bull & prev_bear
        & (y["mid_open"]<=prev_close)
        & (y["mid_close"]>=prev_open)
        & (body>=prev_body*1.05)
    )
    bear_engulf=(
        bear & prev_bull
        & (y["mid_open"]>=prev_close)
        & (y["mid_close"]<=prev_open)
        & (body>=prev_body*1.05)
    )

    hammer=(
        (lower>=body*2.0)
        & (upper<=body*1.0)
        & (lower_pct>=0.45)
        & (body_pct>=0.12)
    )
    shooting=(
        (upper>=body*2.0)
        & (lower<=body*1.0)
        & (upper_pct>=0.45)
        & (body_pct>=0.12)
    )
    doji=body_pct<=0.10
    inside=(y["mid_high"]<y["mid_high"].shift(1))&(y["mid_low"]>y["mid_low"].shift(1))
    outside=(y["mid_high"]>y["mid_high"].shift(1))&(y["mid_low"]<y["mid_low"].shift(1))
    bull_disp=bull&(body_pct>=0.75)&(body>=atr*0.80)
    bear_disp=bear&(body_pct>=0.75)&(body>=atr*0.80)

    pattern=np.full(len(y),"NONE",dtype=object)
    bias=np.zeros(len(y),dtype=int)
    quality=np.zeros(len(y),dtype=int)

    def apply(mask,name,b,q):
        nonlocal pattern,bias,quality
        m=mask.fillna(False).to_numpy() if hasattr(mask,"fillna") else np.asarray(mask,dtype=bool)
        replace=m&(quality<q)
        pattern[replace]=name
        bias[replace]=b
        quality[replace]=q

    apply(doji,"DOJI",0,20)
    apply(inside,"INSIDE_BAR",0,30)
    apply(outside,"OUTSIDE_BAR",0,35)
    apply(bull_disp,"BULLISH_DISPLACEMENT_CANDLE",1,55)
    apply(bear_disp,"BEARISH_DISPLACEMENT_CANDLE",-1,55)
    apply(hammer&bull,"HAMMER",1,60)
    apply(hammer&bear,"BULLISH_REJECTION_PIN",1,58)
    apply(shooting&bear,"SHOOTING_STAR",-1,60)
    apply(shooting&bull,"BEARISH_REJECTION_PIN",-1,58)
    apply(bull_engulf,"BULLISH_ENGULFING",1,70)
    apply(bear_engulf,"BEARISH_ENGULFING",-1,70)

    y["candlestick_pattern"]=pattern
    y["candlestick_bias"]=bias
    y["candlestick_quality"]=quality
    y["candle_body_pct"]=body_pct
    y["upper_wick_pct"]=upper_pct
    y["lower_wick_pct"]=lower_pct
    return y


def annotate_chart_patterns(x: pd.DataFrame) -> pd.DataFrame:
    """Attach causal structural chart-pattern labels to completed bars."""
    y=x.copy()
    n=len(y)
    chart=np.full(n,"NONE",dtype=object)
    bias=np.zeros(n,dtype=int)
    quality=np.zeros(n,dtype=int)
    status=np.full(n,"NONE",dtype=object)
    invalidation=np.full(n,np.nan,dtype=float)

    highs=y["mid_high"].to_numpy(float)
    lows=y["mid_low"].to_numpy(float)
    closes=y["mid_close"].to_numpy(float)
    atr=y["atr14"].to_numpy(float)

    # Confirmed pivots: pivot at i-1 becomes known only at completed bar i.
    high_pivots:list[tuple[int,float]]=[]
    low_pivots:list[tuple[int,float]]=[]

    for i in range(2,n):
        a=max(_safe(atr[i]),1e-9)
        if highs[i-1]>highs[i-2] and highs[i-1]>=highs[i]:
            high_pivots.append((i-1,highs[i-1]))
        if lows[i-1]<lows[i-2] and lows[i-1]<=lows[i]:
            low_pivots.append((i-1,lows[i-1]))

        # Break-and-retest of the level known before the breakout.
        if i>=22:
            prior_hi=float(np.max(highs[i-21:i-1]))
            prior_lo=float(np.min(lows[i-21:i-1]))
            prev_close=closes[i-1]
            if prev_close>prior_hi and lows[i]<=prior_hi+0.15*a and closes[i]>prior_hi:
                chart[i]="BULLISH_BREAK_RETEST";bias[i]=1;quality[i]=82;status[i]="CONFIRMED";invalidation[i]=prior_hi-0.25*a
            elif prev_close<prior_lo and highs[i]>=prior_lo-0.15*a and closes[i]<prior_lo:
                chart[i]="BEARISH_BREAK_RETEST";bias[i]=-1;quality[i]=82;status[i]="CONFIRMED";invalidation[i]=prior_lo+0.25*a

        # Double top/bottom are first treated as liquidity structures; only a
        # neckline close upgrades them to confirmed reversal geometry.
        recent_h=[p for p in high_pivots if p[0]<=i-1 and p[0]>=i-80]
        if len(recent_h)>=2:
            p1,p2=recent_h[-2],recent_h[-1]
            if p2[0]-p1[0]>=3 and abs(p2[1]-p1[1])<=0.30*a:
                valley=float(np.min(lows[p1[0]:p2[0]+1]))
                if chart[i]=="NONE" or quality[i]<78:
                    chart[i]="DOUBLE_TOP_LIQUIDITY";bias[i]=-1;quality[i]=68;status[i]="DEVELOPING";invalidation[i]=max(p1[1],p2[1])+0.20*a
                if closes[i]<valley:
                    chart[i]="DOUBLE_TOP_BREAK";bias[i]=-1;quality[i]=78;status[i]="CONFIRMED";invalidation[i]=max(p1[1],p2[1])+0.20*a

        recent_l=[p for p in low_pivots if p[0]<=i-1 and p[0]>=i-80]
        if len(recent_l)>=2:
            p1,p2=recent_l[-2],recent_l[-1]
            if p2[0]-p1[0]>=3 and abs(p2[1]-p1[1])<=0.30*a:
                peak=float(np.max(highs[p1[0]:p2[0]+1]))
                if chart[i]=="NONE" or quality[i]<78:
                    chart[i]="DOUBLE_BOTTOM_LIQUIDITY";bias[i]=1;quality[i]=68;status[i]="DEVELOPING";invalidation[i]=min(p1[1],p2[1])-0.20*a
                if closes[i]>peak:
                    chart[i]="DOUBLE_BOTTOM_BREAK";bias[i]=1;quality[i]=78;status[i]="CONFIRMED";invalidation[i]=min(p1[1],p2[1])-0.20*a

        # Head-and-shoulders / inverse H&S using three confirmed pivots. This
        # is intentionally strict and only labels after the third pivot exists.
        if len(recent_h)>=3:
            lft,head,rgt=recent_h[-3:]
            shoulder_tol=0.40*a
            if head[1]>lft[1]+0.25*a and head[1]>rgt[1]+0.25*a and abs(lft[1]-rgt[1])<=shoulder_tol:
                left_valley=float(np.min(lows[lft[0]:head[0]+1]))
                right_valley=float(np.min(lows[head[0]:rgt[0]+1]))
                neckline=(left_valley+right_valley)/2.0
                if chart[i]=="NONE" or quality[i]<84:
                    chart[i]="HEAD_AND_SHOULDERS";bias[i]=-1;quality[i]=76;status[i]="DEVELOPING";invalidation[i]=head[1]+0.20*a
                if closes[i]<neckline:
                    chart[i]="HEAD_AND_SHOULDERS_BREAK";bias[i]=-1;quality[i]=84;status[i]="CONFIRMED";invalidation[i]=head[1]+0.20*a

        if len(recent_l)>=3:
            lft,head,rgt=recent_l[-3:]
            shoulder_tol=0.40*a
            if head[1]<lft[1]-0.25*a and head[1]<rgt[1]-0.25*a and abs(lft[1]-rgt[1])<=shoulder_tol:
                left_peak=float(np.max(highs[lft[0]:head[0]+1]))
                right_peak=float(np.max(highs[head[0]:rgt[0]+1]))
                neckline=(left_peak+right_peak)/2.0
                if chart[i]=="NONE" or quality[i]<84:
                    chart[i]="INVERSE_HEAD_AND_SHOULDERS";bias[i]=1;quality[i]=76;status[i]="DEVELOPING";invalidation[i]=head[1]-0.20*a
                if closes[i]>neckline:
                    chart[i]="INVERSE_HEAD_AND_SHOULDERS_BREAK";bias[i]=1;quality[i]=84;status[i]="CONFIRMED";invalidation[i]=head[1]-0.20*a

        # Objective compression geometry from rolling high/low trendlines.
        if i>=30 and (chart[i]=="NONE" or quality[i]<70):
            wh=highs[i-19:i+1]
            wl=lows[i-19:i+1]
            old_h=highs[i-39:i-19] if i>=39 else highs[max(0,i-29):i-9]
            old_l=lows[i-39:i-19] if i>=39 else lows[max(0,i-29):i-9]
            hs=_line_slope(wh)/a
            ls=_line_slope(wl)/a
            current_range=float(np.max(wh)-np.min(wl))
            old_range=float(np.max(old_h)-np.min(old_l)) if len(old_h)>=5 else current_range
            contracted=old_range>0 and current_range<=old_range*0.85
            flat_tol=0.015
            if contracted and hs<-0.01 and ls>0.01:
                chart[i]="SYMMETRICAL_TRIANGLE";bias[i]=0;quality[i]=66;status[i]="DEVELOPING"
            elif contracted and abs(hs)<=flat_tol and ls>0.01:
                chart[i]="ASCENDING_TRIANGLE";bias[i]=1;quality[i]=70;status[i]="DEVELOPING"
            elif contracted and hs<-0.01 and abs(ls)<=flat_tol:
                chart[i]="DESCENDING_TRIANGLE";bias[i]=-1;quality[i]=70;status[i]="DEVELOPING"
            elif hs>0.02 and ls>0.02 and abs(hs-ls)<=0.05:
                chart[i]="RISING_CHANNEL";bias[i]=1;quality[i]=55;status[i]="ACTIVE"
            elif hs<-0.02 and ls<-0.02 and abs(hs-ls)<=0.05:
                chart[i]="FALLING_CHANNEL";bias[i]=-1;quality[i]=55;status[i]="ACTIVE"

    y["chart_pattern"]=chart
    y["chart_pattern_bias"]=bias
    y["chart_pattern_quality"]=quality
    y["chart_pattern_status"]=status
    y["chart_pattern_invalidation"]=invalidation
    return y


def annotate_patterns(x: pd.DataFrame) -> pd.DataFrame:
    return annotate_chart_patterns(annotate_candlesticks(x))


def latest_pattern_state(x: pd.DataFrame) -> dict:
    if x.empty:
        return {}
    r=x.iloc[-1]
    return {
        "candlestick":{
            "pattern":str(r.get("candlestick_pattern","NONE")),
            "bias":int(r.get("candlestick_bias",0)),
            "quality":int(r.get("candlestick_quality",0)),
        },
        "chart":{
            "pattern":str(r.get("chart_pattern","NONE")),
            "bias":int(r.get("chart_pattern_bias",0)),
            "quality":int(r.get("chart_pattern_quality",0)),
            "status":str(r.get("chart_pattern_status","NONE")),
            "invalidation":None if not np.isfinite(_safe(r.get("chart_pattern_invalidation"),np.nan)) else float(r.get("chart_pattern_invalidation")),
        },
        "authority":"CLOSED_BAR_DETERMINISTIC_PATTERN_EVIDENCE",
        "executionEligible":False,
    }
