import type { CandlePack } from './candles.ts';
export type Plan={symbol:string;direction:'BUY'|'SELL';entryLow:number;entryHigh:number;stop:number;target:number;createdAt:number;expiresAt:number};
export type Observation={state:string;lastCandle:number|null;entryTouchTime:number|null;terminalTime:number|null;favorableR:number|null;adverseR:number|null;reason:string};
// Price-path observations only. This never models fills, slippage, spread or P&L.
export function observePlan(plan:Plan,pack:CandlePack,now=Date.now()):Observation {
  const out:Observation={state:'WATCH',lastCandle:null,entryTouchTime:null,terminalTime:null,favorableR:null,adverseR:null,reason:'Waiting for an observed entry-zone touch.'};
  if(pack.symbol!==plan.symbol)throw new Error('INSTRUMENT_MISMATCH');
  if(![plan.entryLow,plan.entryHigh,plan.stop,plan.target,plan.createdAt,plan.expiresAt].every(Number.isFinite)||plan.entryLow<=0||plan.entryLow>plan.entryHigh||plan.expiresAt<=plan.createdAt)throw new Error('INVALID_PLAN');
  const entry=plan.direction==='BUY'?plan.entryHigh:plan.entryLow;
  const risk=plan.direction==='BUY'?entry-plan.stop:plan.stop-entry;
  const reward=plan.direction==='BUY'?plan.target-entry:entry-plan.target;
  if(risk<=0||reward/risk<1.5||(plan.direction==='BUY'?plan.stop>=plan.entryLow:plan.stop<=plan.entryHigh))throw new Error('INVALID_PLAN_GEOMETRY');
  // A candle containing the scan creation instant may include pre-scan prices.
  const start=Math.ceil(plan.createdAt/pack.intervalMs)*pack.intervalMs;
  if(!pack.candles.length||pack.candles[0].time>start)return {...out,state:'DATA_GAP',reason:'Provider history does not cover the start of observation.'};
  const candles=pack.candles.filter(c=>c.time>=start&&c.time+pack.intervalMs<=Math.min(now,plan.expiresAt));
  for(const c of candles) {
    out.lastCandle=c.time;
    const touches=c.low<=plan.entryHigh&&c.high>=plan.entryLow;
    const stop=plan.direction==='BUY'?c.low<=plan.stop:c.high>=plan.stop;
    const target=plan.direction==='BUY'?c.high>=plan.target:c.low<=plan.target;
    if(out.entryTouchTime===null) {
      if(!touches)continue;
      out.entryTouchTime=c.time; out.state='ENTRY_TOUCHED';out.reason='Entry zone touched in a closed candle; no fill is assumed.';
      if(stop||target) return {...out,state:'AMBIGUOUS',terminalTime:c.time,reason:'Entry and a terminal level share one candle; ordering is unknowable.'};
      out.favorableR=0;out.adverseR=0;continue;
    }
    if(stop&&target)return {...out,state:'AMBIGUOUS',terminalTime:c.time,reason:'Stop and target share one candle; ordering is unknowable.'};
    if(stop||target)return {...out,state:stop?'STOP_TOUCHED':'TARGET_TOUCHED',terminalTime:c.time,reason:'Observed level touch, not a verified trade outcome. Excursions exclude terminal candle.'};
    out.favorableR=Math.max(out.favorableR||0,(plan.direction==='BUY'?c.high-entry:entry-c.low)/risk,0);
    out.adverseR=Math.max(out.adverseR||0,(plan.direction==='BUY'?entry-c.low:c.high-entry)/risk,0);
  }
  if(now>=plan.expiresAt)return {...out,state:'EXPIRED',reason:'Observation window ended without a resolved price path.'};
  return out;
}
export function summarizeObservations(rows:Observation[]) {
  const counts=Object.fromEntries(['WATCH','ENTRY_TOUCHED','TARGET_TOUCHED','STOP_TOUCHED','AMBIGUOUS','EXPIRED','DATA_GAP'].map(s=>[s,rows.filter(r=>r.state===s).length]));
  return {sampleCount:rows.length,counts,winRate:null,expectancy:null,profitFactor:null,explanation:'Counts describe reference-market price paths, not executed trades. No profitability statistics are inferred.'};
}
