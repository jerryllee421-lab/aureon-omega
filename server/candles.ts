export type Candle = {time:number;open:number;high:number;low:number;close:number};
export type CandlePack = {symbol:string;provider:string;providerInstrument:string;intervalMs:number;observedAt:number;candles:Candle[]};
export function validateCandles(rows:Candle[], intervalMs:number, now=Date.now(), minimum=3):Candle[] {
  if (!Number.isInteger(intervalMs)||intervalMs<=0) throw new Error('INVALID_INTERVAL');
  if (rows.some(c=>![c.time,c.open,c.high,c.low,c.close].every(Number.isFinite)||c.time<0||c.time>now+5000||c.time%intervalMs!==0||Math.min(c.open,c.high,c.low,c.close)<=0||c.high<Math.max(c.open,c.close,c.low)||c.low>Math.min(c.open,c.close,c.high))) throw new Error('INVALID_CANDLE');
  const closed=rows.filter(c=>c.time+intervalMs<=now);
  if(closed.length<minimum)throw new Error('INSUFFICIENT_CLOSED_CANDLES');
  for(let i=1;i<closed.length;i++)if(closed[i].time-closed[i-1].time!==intervalMs)throw new Error('CANDLE_GAP_OR_DUPLICATE');
  const age=now-(closed.at(-1)!.time+intervalMs);
  if(age<0||age>intervalMs*2)throw new Error('STALE_CANDLES');
  return closed;
}
export async function acquireCandles(symbol:string):Promise<CandlePack> {
  const observedAt=Date.now(), intervalMs=300000;
  if(symbol==='BTCUSD') {
    const r=await fetch('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=5',{signal:AbortSignal.timeout(12000)});
    if(!r.ok)throw new Error('BTC_CANDLES_UNAVAILABLE');
    const body=await r.json(); const rows=body.result?.XXBTZUSD;
    if(body.error?.length||!Array.isArray(rows))throw new Error('BTC_INSTRUMENT_UNVERIFIED');
    const candles=validateCandles(rows.slice(0,-1).map((v:unknown[])=>({time:Number(v[0])*1000,open:Number(v[1]),high:Number(v[2]),low:Number(v[3]),close:Number(v[4])})),intervalMs,observedAt);
    return {symbol,provider:'Kraken',providerInstrument:'XXBTZUSD',intervalMs,observedAt,candles};
  }
  if(symbol==='XAUUSD') {
    if(!process.env.TWELVE_DATA_API_KEY)throw new Error('GOLD_CANDLES_UNCONFIGURED');
    const query=new URLSearchParams({symbol:'XAU/USD',interval:'5min',outputsize:'200',timezone:'UTC',apikey:process.env.TWELVE_DATA_API_KEY});
    const r=await fetch('https://api.twelvedata.com/time_series?'+query,{signal:AbortSignal.timeout(12000)});
    if(!r.ok)throw new Error('GOLD_CANDLES_UNAVAILABLE');
    const body=await r.json();
    if(body.meta?.symbol!=='XAU/USD'||!Array.isArray(body.values))throw new Error('GOLD_INSTRUMENT_UNVERIFIED');
    const candles=validateCandles(body.values.map((v:any)=>({time:Date.parse(v.datetime.replace(' ','T')+'Z'),open:Number(v.open),high:Number(v.high),low:Number(v.low),close:Number(v.close)})).reverse(),intervalMs,observedAt);
    return {symbol,provider:'Twelve Data',providerInstrument:'XAU/USD',intervalMs,observedAt,candles};
  }
  throw new Error('EXACT_INSTRUMENT_UNSUPPORTED');
}