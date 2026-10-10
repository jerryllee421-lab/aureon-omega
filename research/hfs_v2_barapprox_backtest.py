from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd

POINT=0.01
LOT=0.01
CONTRACT=100.0
USD_PER_PRICE=LOT*CONTRACT
ENTRY_SCORE_BASE=62.0
EDGE_MARGIN=8.0
MAX_SPREAD_POINTS=80.0
INITIAL_SL_ATR_MULT=1.40
MAX_SL_POINTS=650.0
SWING_BUFFER_POINTS=8.0
COMMISSION_ROUND_PER_LOT=7.0
SLIPPAGE_POINTS=10.0
COST_BUFFER=0.05
LOCK_TRIGGER=1.25
BE_COST_MULT=1.10
STALL_BARS=1
MAX_TARGET_ATR_MULT=2.50
MAX_CONSEC_LOSSES=6
DAILY_LOSS_PCT=3.0
MAX_DD_PCT=6.0
START_BALANCE=10000.0


def load_months(root: Path, start='2016-01-01', end='2025-12-31') -> pd.DataFrame:
    parts=[]
    for side in ('bid','ask'):
        files=sorted((root/'xauusd'/side/'m1').glob(f'xauusd_{side}_m1_*.csv'))
        if not files:
            raise SystemExit(f'no {side} files under {root}')
        frames=[]
        for f in files:
            ym=f.stem.rsplit('_',2)[-2:]
            y,m=int(ym[0]),int(ym[1])
            if y<2016 or y>2025:
                continue
            x=pd.read_csv(f)
            x['time']=pd.to_datetime(x['timestamp'],unit='ms',utc=True)
            x=x[['time','open','high','low','close']].rename(columns={c:f'{c}_{side}' for c in ['open','high','low','close']})
            frames.append(x)
        z=pd.concat(frames,ignore_index=True).sort_values('time').drop_duplicates('time')
        parts.append(z)
    df=parts[0].merge(parts[1],on='time',how='inner')
    df=df[(df.time>=pd.Timestamp(start,tz='UTC')) & (df.time<=pd.Timestamp(end+' 23:59:59',tz='UTC'))].copy()
    if df.empty:
        raise SystemExit('empty merged range')
    return df.reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x=df.copy()
    c=x.close_bid.astype(float); h=x.high_bid.astype(float); l=x.low_bid.astype(float); o=x.open_bid.astype(float)
    for n in (9,21,55,100,200):
        x[f'ema{n}']=c.ewm(span=n,adjust=False,min_periods=n).mean()
    prev=c.shift(1)
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    x['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    typical=(h+l+c)/3.0
    x['vwap20']=typical.shift(1).rolling(20,min_periods=20).mean()
    x['spread_open']=x.open_ask-x.open_bid
    x['spread_close']=x.close_ask-x.close_bid
    x['recent_high']=h.shift(2).rolling(9,min_periods=9).max()
    x['recent_low']=l.shift(2).rolling(9,min_periods=9).min()
    x['breakout_high']=h.shift(2).rolling(5,min_periods=5).max()
    x['breakout_low']=l.shift(2).rolling(5,min_periods=5).min()
    x['open1']=o.shift(1); x['close1']=c.shift(1); x['high1']=h.shift(1); x['low1']=l.shift(1)
    x['high3']=h.shift(3); x['low3']=l.shift(3)
    rng=x.high1-x.low1
    x['body_eff']=((x.close1-x.open1).abs()/rng.replace(0,np.nan)).fillna(0.0)
    x['volume_ratio']=1.0
    return x


def rr_floor(score):
    if score>=82: return 1.35
    if score>=74: return 1.25
    if score>=68: return 1.15
    return 1.05


def score_row(r):
    bf={k:0.0 for k in ('trend','structure','liquidity','momentum','value','volatility','execution')}
    sf={k:0.0 for k in bf}
    if r.ema9>r.ema21>r.ema55: bf['trend']+=10
    if r.ema9<r.ema21<r.ema55: sf['trend']+=10
    if r.ema9>r.ema9_prev and r.ema21>r.ema21_prev: bf['trend']+=4
    if r.ema9<r.ema9_prev and r.ema21<r.ema21_prev: sf['trend']+=4
    if r.close1>r.ema100: bf['trend']+=4
    if r.close1<r.ema100: sf['trend']+=4
    if r.close1>r.ema200: bf['trend']+=2
    if r.close1<r.ema200: sf['trend']+=2
    bf['trend']=min(20,bf['trend']); sf['trend']=min(20,sf['trend'])
    if r.low1>r.high3: bf['structure']=max(bf['structure'],12)
    if r.high1<r.low3: sf['structure']=max(sf['structure'],12)
    if r.close1>r.breakout_high: bf['structure']=max(bf['structure'],18)
    if r.close1<r.breakout_low: sf['structure']=max(sf['structure'],18)
    if r.low1<r.recent_low and r.close1>r.recent_low: bf['liquidity']=16
    if r.high1>r.recent_high and r.close1<r.recent_high: sf['liquidity']=16
    if r.body_eff>=0.60:
        if r.close1>r.open1: bf['momentum']+=9
        elif r.close1<r.open1: sf['momentum']+=9
    bf['momentum']=min(14,bf['momentum']); sf['momentum']=min(14,sf['momentum'])
    if r.close1>r.vwap20: bf['value']=10
    if r.close1<r.vwap20: sf['value']=10
    atr_points=r.atr/POINT if r.atr>0 else 0
    if 20<=atr_points<=3000: bf['volatility']=sf['volatility']=10
    spread_to_atr=r.spread_open/r.atr if r.atr>0 else 1
    if spread_to_atr<=0.10: bf['execution']=sf['execution']=12
    elif spread_to_atr<=0.15: bf['execution']=sf['execution']=6
    threshold=ENTRY_SCORE_BASE
    if spread_to_atr>0.12: threshold+=5
    if r.body_eff>0.72 and r.volume_ratio>1.20: threshold-=2
    threshold=max(58,min(75,threshold))
    buy=min(100,sum(bf.values())); sell=min(100,sum(sf.values()))
    direction=0; score=0
    if buy>=threshold and buy-sell>=EDGE_MARGIN: direction=1; score=buy
    elif sell>=threshold and sell-buy>=EDGE_MARGIN: direction=-1; score=sell
    return buy,sell,threshold,direction,score


def pnl_at(direction,entry,exitpx):
    gross=(exitpx-entry)*USD_PER_PRICE*direction
    return gross - COMMISSION_ROUND_PER_LOT*LOT - SLIPPAGE_POINTS*POINT*USD_PER_PRICE


def run(df: pd.DataFrame):
    df=df.copy()
    for n in (9,21): df[f'ema{n}_prev']=df[f'ema{n}'].shift(1)
    balance=START_BALANCE
    day=None; day_start_balance=START_BALANCE; realized_today=0.0; cons_losses=0
    pos=None; last_event=None
    trades=[]; blocks={'score':0,'spread':0,'fresh':0,'economics':0,'risk':0}
    warm=220
    for i in range(warm,len(df)):
        r=df.iloc[i]
        vals=[r.atr,r.ema9,r.ema21,r.ema55,r.ema100,r.ema200,r.vwap20,r.recent_high,r.recent_low,r.breakout_high,r.breakout_low]
        if not np.isfinite(vals).all():
            continue
        d=r.time.date()
        if d!=day:
            day=d; day_start_balance=balance; realized_today=0.0; cons_losses=0
        buy,sell,threshold,direction,score=score_row(r)

        if pos is not None:
            qlow=r.low_bid if pos['dir']>0 else r.low_ask
            qhigh=r.high_bid if pos['dir']>0 else r.high_ask
            hit_sl=(qlow<=pos['sl']) if pos['dir']>0 else (qhigh>=pos['sl'])
            hit_tp=(qhigh>=pos['tp']) if pos['dir']>0 else (qlow<=pos['tp'])
            reason=None
            if hit_sl:
                exitpx=pos['sl']; reason='SL'
            elif hit_tp:
                exitpx=pos['tp']; reason='TP'
            else:
                fav=(qhigh-pos['entry'])*USD_PER_PRICE if pos['dir']>0 else (pos['entry']-qlow)*USD_PER_PRICE
                adv=(qlow-pos['entry'])*USD_PER_PRICE if pos['dir']>0 else (pos['entry']-qhigh)*USD_PER_PRICE
                pos['mfe']=max(pos['mfe'],fav); pos['mae']=min(pos['mae'],adv)
                exit_quote=r.close_bid if pos['dir']>0 else r.close_ask
                gross_float=(exit_quote-pos['entry'])*USD_PER_PRICE*pos['dir']
                pos['peak']=max(pos['peak'],gross_float)
                floor=pos['entry_cost']
                side=buy if pos['dir']>0 else sell; opp=sell if pos['dir']>0 else buy
                held=i-pos['entry_i']
                retr=max(0,pos['peak']-gross_float); retr_ratio=retr/pos['peak'] if pos['peak']>0 else 0
                if pos['entry_score']>=80 and side>=72 and r.body_eff>=0.60 and r.volume_ratio>=1.05:
                    pos['mode']='RUNNER'
                elif pos['mode']=='MICRO' and side>=72 and gross_float>=floor:
                    pos['mode']='STANDARD'
                if gross_float>=floor*LOCK_TRIGGER:
                    cost_dist=(floor*BE_COST_MULT)/USD_PER_PRICE
                    desired=(max(pos['entry']+cost_dist,r.close_bid-r.atr*0.45) if pos['dir']>0 else min(pos['entry']-cost_dist,r.close_ask+r.atr*0.45))
                    if pos['dir']>0 and desired>pos['entry'] and desired>pos['sl']: pos['sl']=desired
                    if pos['dir']<0 and desired<pos['entry'] and desired<pos['sl']: pos['sl']=desired
                if held>=1 and gross_float<0 and opp>=70 and opp-side>=15: reason='FAILURE'
                elif held>=STALL_BARS and gross_float<floor*0.25 and side<threshold: reason='FAILURE'
                elif gross_float>=floor and opp>side+12: reason=pos['mode']
                elif pos['mode']=='MICRO' and gross_float>=floor and ((pos['entry_score']>0 and side<=pos['entry_score']-8) or retr_ratio>=0.20 or held>=1): reason='MICRO'
                elif pos['mode']=='MICRO' and gross_float>=floor*1.60: reason='MICRO'
                elif pos['mode']=='STANDARD' and gross_float>=floor*2.50 and (retr_ratio>=0.30 or side<58): reason='STANDARD'
                elif pos['mode']=='STANDARD' and gross_float>=floor*4.00: reason='STANDARD'
                elif pos['mode']=='RUNNER' and gross_float>=floor*4.00 and retr_ratio>=0.40: reason='RUNNER'
                elif pos['mode']=='RUNNER' and gross_float>=floor and side<55: reason='RUNNER'
                if reason: exitpx=exit_quote
            if reason:
                net=pnl_at(pos['dir'],pos['entry'],exitpx)
                balance+=net; realized_today+=net
                cons_losses=cons_losses+1 if net<0 else (0 if net>0 else cons_losses)
                trades.append({**pos,'exit_time':r.time,'exit':exitpx,'pnl':net,'reason':reason,'hold_min':i-pos['entry_i'],'year':r.time.year,'month':r.time.strftime('%Y-%m'),'hour':r.time.hour})
                last_event=pos['event']; pos=None
                continue

        if direction==0:
            blocks['score']+=1; continue
        spread_points=r.spread_open/POINT
        if spread_points>MAX_SPREAD_POINTS:
            blocks['spread']+=1; continue
        event=int(r.time.timestamp())*10+(1 if direction>0 else 2)
        if last_event is not None and event==last_event:
            blocks['fresh']+=1; continue
        if realized_today<=-(day_start_balance*DAILY_LOSS_PCT/100) or cons_losses>=MAX_CONSEC_LOSSES:
            blocks['risk']+=1; continue
        entry=r.open_ask if direction>0 else r.open_bid
        atr_stop=(r.open_bid-r.atr*INITIAL_SL_ATR_MULT) if direction>0 else (r.open_ask+r.atr*INITIAL_SL_ATR_MULT)
        swing=(r.recent_low-SWING_BUFFER_POINTS*POINT) if direction>0 else (r.recent_high+SWING_BUFFER_POINTS*POINT)
        sl=min(atr_stop,swing) if direction>0 else max(atr_stop,swing)
        max_dist=MAX_SL_POINTS*POINT
        if abs(entry-sl)>max_dist: sl=entry-max_dist if direction>0 else entry+max_dist
        risk_dist=abs(entry-sl)
        if risk_dist<=0: blocks['economics']+=1; continue
        spread_cost=r.spread_open*USD_PER_PRICE
        entry_cost=spread_cost+COMMISSION_ROUND_PER_LOT*LOT+SLIPPAGE_POINTS*POINT*USD_PER_PRICE+COST_BUFFER
        cost_dist=entry_cost/USD_PER_PRICE
        target_dist=risk_dist*rr_floor(score)+cost_dist
        if target_dist>r.atr*MAX_TARGET_ATR_MULT:
            blocks['economics']+=1; continue
        tp=entry+target_dist if direction>0 else entry-target_dist
        mode='MICRO' if score<68 else ('RUNNER' if score>=82 else 'STANDARD')
        pos={'dir':direction,'entry':entry,'sl':sl,'tp':tp,'entry_time':r.time,'entry_i':i,'entry_score':score,'buy_score':buy,'sell_score':sell,'event':event,'entry_cost':entry_cost,'entry_spread':r.spread_open,'entry_atr':r.atr,'mfe':0.0,'mae':0.0,'peak':0.0,'mode':mode}

    if pos is not None:
        r=df.iloc[-1]; exitpx=r.close_bid if pos['dir']>0 else r.close_ask
        net=pnl_at(pos['dir'],pos['entry'],exitpx); balance+=net
        trades.append({**pos,'exit_time':r.time,'exit':exitpx,'pnl':net,'reason':'END_OF_TEST','hold_min':len(df)-1-pos['entry_i'],'year':r.time.year,'month':r.time.strftime('%Y-%m'),'hour':r.time.hour})

    t=pd.DataFrame(trades)
    if t.empty: raise SystemExit('no trades')
    t['win']=t.pnl>0
    t['cum']=t.pnl.cumsum()+START_BALANCE
    t['peak_eq']=t['cum'].cummax(); t['dd']=t['peak_eq']-t['cum']; t['dd_pct']=100*t['dd']/t['peak_eq']
    gp=t.loc[t.pnl>0,'pnl'].sum(); gl=-t.loc[t.pnl<0,'pnl'].sum()
    summary={
      'data_fidelity':'BAR_APPROX_BID_ASK_M1_NO_TICK_VOLUME',
      'period_start':str(df.time.iloc[0]),'period_end':str(df.time.iloc[-1]),'bars':int(len(df)),
      'trades':int(len(t)),'wins':int(t.win.sum()),'losses':int((~t.win).sum()),'win_rate_pct':float(100*t.win.mean()),
      'net_profit':float(t.pnl.sum()),'ending_balance':float(START_BALANCE+t.pnl.sum()),
      'gross_profit':float(gp),'gross_loss':float(gl),'profit_factor':float(gp/gl if gl>0 else math.inf),
      'avg_trade':float(t.pnl.mean()),'avg_win':float(t.loc[t.pnl>0,'pnl'].mean()),'avg_loss':float(t.loc[t.pnl<0,'pnl'].mean()),
      'payoff_ratio':float(t.loc[t.pnl>0,'pnl'].mean()/abs(t.loc[t.pnl<0,'pnl'].mean())),
      'max_drawdown_pct':float(t.dd_pct.max()),'max_drawdown_money':float(t.dd.max()),
      'median_hold_min':float(t.hold_min.median()),'mean_hold_min':float(t.hold_min.mean()),
      'long_trades':int((t.dir>0).sum()),'short_trades':int((t.dir<0).sum()),'blocks':blocks,
    }
    yearly=t.groupby('year').agg(trades=('pnl','size'),net=('pnl','sum'),win_rate=('win','mean'),gross_profit=('pnl',lambda s:s[s>0].sum()),gross_loss=('pnl',lambda s:-s[s<0].sum()),max_dd_pct=('dd_pct','max')).reset_index()
    yearly['pf']=yearly.gross_profit/yearly.gross_loss.replace(0,np.nan); yearly['win_rate']*=100
    monthly=t.groupby('month').agg(trades=('pnl','size'),net=('pnl','sum'),win_rate=('win','mean'),gross_profit=('pnl',lambda s:s[s>0].sum()),gross_loss=('pnl',lambda s:-s[s<0].sum())).reset_index(); monthly['pf']=monthly.gross_profit/monthly.gross_loss.replace(0,np.nan); monthly['win_rate']*=100
    hours=t.groupby('hour').agg(trades=('pnl','size'),net=('pnl','sum'),win_rate=('win','mean'),gross_profit=('pnl',lambda s:s[s>0].sum()),gross_loss=('pnl',lambda s:-s[s<0].sum())).reset_index(); hours['pf']=hours.gross_profit/hours.gross_loss.replace(0,np.nan); hours['win_rate']*=100
    reasons=t.groupby('reason').agg(trades=('pnl','size'),net=('pnl','sum'),win_rate=('win','mean'),avg=('pnl','mean')).reset_index(); reasons['win_rate']*=100
    directions=t.groupby('dir').agg(trades=('pnl','size'),net=('pnl','sum'),win_rate=('win','mean'),gross_profit=('pnl',lambda s:s[s>0].sum()),gross_loss=('pnl',lambda s:-s[s<0].sum())).reset_index(); directions['pf']=directions.gross_profit/directions.gross_loss.replace(0,np.nan); directions['win_rate']*=100
    return summary,t,yearly,monthly,hours,reasons,directions


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-root',required=True); ap.add_argument('--out',default='hfs_v2_results'); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    df=add_features(load_months(Path(a.data_root)))
    summary,trades,yearly,monthly,hours,reasons,directions=run(df)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    trades.to_csv(out/'trades.csv',index=False); yearly.to_csv(out/'yearly.csv',index=False); monthly.to_csv(out/'monthly.csv',index=False); hours.to_csv(out/'hours.csv',index=False); reasons.to_csv(out/'exit_reasons.csv',index=False); directions.to_csv(out/'directions.csv',index=False)
    print(json.dumps(summary,indent=2)); print('\nYEARLY\n',yearly.to_string(index=False)); print('\nDIRECTIONS\n',directions.to_string(index=False)); print('\nEXITS\n',reasons.to_string(index=False))

if __name__=='__main__': main()
