import {acquireCandles,intervalLabel,type Candle,type CandlePack,type SupportedInterval} from './candles.ts';

const round=(v:number|null,d=6)=>v===null?null:Number(v.toFixed(d));
const sma=(values:number[])=>values.reduce((a,b)=>a+b,0)/values.length;

export function emaLatest(values:number[],period:number):number|null{
  if(values.length<period)return null;
  let value=sma(values.slice(0,period));const k=2/(period+1);
  for(let i=period;i<values.length;i++)value=values[i]*k+value*(1-k);
  return value;
}

export function rsiLatest(values:number[],period=14):number|null{
  if(values.length<=period)return null;
  let gain=0,loss=0;
  for(let i=1;i<=period;i++){const d=values[i]-values[i-1];if(d>0)gain+=d;else loss-=d;}
  let avgGain=gain/period,avgLoss=loss/period;
  for(let i=period+1;i<values.length;i++){const d=values[i]-values[i-1],g=Math.max(d,0),l=Math.max(-d,0);avgGain=(avgGain*(period-1)+g)/period;avgLoss=(avgLoss*(period-1)+l)/period;}
  if(avgLoss===0)return 100;
  const rs=avgGain/avgLoss;return 100-(100/(1+rs));
}

export function atrLatest(candles:Candle[],period=14):number|null{
  if(candles.length<=period)return null;
  const tr:number[]=[];
  for(let i=1;i<candles.length;i++)tr.push(Math.max(candles[i].high-candles[i].low,Math.abs(candles[i].high-candles[i-1].close),Math.abs(candles[i].low-candles[i-1].close)));
  if(tr.length<period)return null;
  let atr=sma(tr.slice(0,period));
  for(let i=period;i<tr.length;i++)atr=(atr*(period-1)+tr[i])/period;
  return atr;
}

export function adxLatest(candles:Candle[],period=14):number|null{
  if(candles.length<period*2+1)return null;
  const tr:number[]=[],plus:number[]=[],minus:number[]=[];
  for(let i=1;i<candles.length;i++){
    const up=candles[i].high-candles[i-1].high,down=candles[i-1].low-candles[i].low;
    plus.push(up>down&&up>0?up:0);minus.push(down>up&&down>0?down:0);
    tr.push(Math.max(candles[i].high-candles[i].low,Math.abs(candles[i].high-candles[i-1].close),Math.abs(candles[i].low-candles[i-1].close)));
  }
  let smTr=tr.slice(0,period).reduce((a,b)=>a+b,0),smPlus=plus.slice(0,period).reduce((a,b)=>a+b,0),smMinus=minus.slice(0,period).reduce((a,b)=>a+b,0);
  const dx:number[]=[];
  const pushDx=()=>{if(smTr<=0){dx.push(0);return;}const p=100*smPlus/smTr,m=100*smMinus/smTr;dx.push(p+m===0?0:100*Math.abs(p-m)/(p+m));};
  pushDx();
  for(let i=period;i<tr.length;i++){smTr=smTr-smTr/period+tr[i];smPlus=smPlus-smPlus/period+plus[i];smMinus=smMinus-smMinus/period+minus[i];pushDx();}
  if(dx.length<period)return null;
  let adx=sma(dx.slice(0,period));for(let i=period;i<dx.length;i++)adx=(adx*(period-1)+dx[i])/period;
  return adx;
}

function structure(candles:Candle[]){
  if(candles.length<20)return 'INSUFFICIENT';
  const block=candles.slice(-20),older=block.slice(0,10),newer=block.slice(10);
  const oldHigh=Math.max(...older.map(c=>c.high)),oldLow=Math.min(...older.map(c=>c.low)),newHigh=Math.max(...newer.map(c=>c.high)),newLow=Math.min(...newer.map(c=>c.low));
  if(newHigh>oldHigh&&newLow>oldLow)return 'HH_HL';
  if(newHigh<oldHigh&&newLow<oldLow)return 'LH_LL';
  return 'MIXED';
}

export function quantSnapshot(pack:CandlePack){
  const candles=pack.candles,closes=candles.map(c=>c.close),last=candles.at(-1)!;
  const ema20=emaLatest(closes,20),ema50=emaLatest(closes,50),rsi14=rsiLatest(closes,14),atr14=atrLatest(candles,14),adx14=adxLatest(candles,14);
  if(ema20===null||ema50===null||rsi14===null||atr14===null||adx14===null)throw new Error('INSUFFICIENT_QUANT_HISTORY');
  const bias=last.close>ema20&&ema20>ema50?'UP':last.close<ema20&&ema20<ema50?'DOWN':'NEUTRAL';
  const regime=adx14>=20&&bias==='UP'?'TREND_UP':adx14>=20&&bias==='DOWN'?'TREND_DOWN':'RANGE_OR_TRANSITION';
  const recent=candles.slice(-20);
  return {
    symbol:pack.symbol,timeframe:intervalLabel(pack.intervalMinutes),intervalMinutes:pack.intervalMinutes,
    provider:pack.provider,providerInstrument:pack.providerInstrument,observedAt:new Date(pack.observedAt).toISOString(),
    lastClosedAt:new Date(last.time+pack.intervalMs).toISOString(),sampleCount:candles.length,
    close:round(last.close),ema20:round(ema20),ema50:round(ema50),rsi14:round(rsi14,2),atr14:round(atr14),atrPercent:round(atr14/last.close*100,3),adx14:round(adx14,2),
    recentHigh:round(Math.max(...recent.map(c=>c.high))),recentLow:round(Math.min(...recent.map(c=>c.low))),structure:structure(candles),bias,regime,
    authority:'CLOSED_CANDLE_REFERENCE',executionEligible:false,
  };
}

export function mtfAlignment(frames:Array<{bias:string}>){
  const up=frames.filter(f=>f.bias==='UP').length,down=frames.filter(f=>f.bias==='DOWN').length,neutral=frames.length-up-down;
  const alignment=frames.length<2?'INSUFFICIENT':up>=3&&down===0?'BULLISH_ALIGNMENT':down>=3&&up===0?'BEARISH_ALIGNMENT':'MIXED';
  return {alignment,up,down,neutral};
}

export async function multiTimeframeQuant(symbol:string){
  if(!['BTCUSD','XAUUSD'].includes(symbol))throw new Error('EXACT_INSTRUMENT_UNSUPPORTED');
  const intervals:SupportedInterval[]=[5,15,60,240];
  const settled=await Promise.allSettled(intervals.map(interval=>acquireCandles(symbol,interval,80,symbol==='BTCUSD')));
  const frames=settled.map((result,index)=>result.status==='fulfilled'
    ?{status:'READY',...quantSnapshot(result.value)}
    :{status:'UNAVAILABLE',symbol,timeframe:intervalLabel(intervals[index]),intervalMinutes:intervals[index],reason:result.reason instanceof Error?result.reason.message:'PROVIDER_UNAVAILABLE',authority:'UNAVAILABLE',executionEligible:false});
  const ready=frames.filter((f:any)=>f.status==='READY') as Array<{bias:string}>;
  return {
    symbol,generatedAt:new Date().toISOString(),authority:'CLOSED_CANDLE_REFERENCE',executionEligible:false,
    explanation:'Deterministic multi-timeframe reference context from closed provider candles. This is not a broker quote, fill model, trade signal or execution authority.',
    mtf:mtfAlignment(ready),frames
  };
}
