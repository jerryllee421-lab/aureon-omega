export type Candle={time:number;open:number;high:number;low:number;close:number};
export type CandlePack={symbol:string;provider:string;providerInstrument:string;intervalMs:number;intervalMinutes:number;observedAt:number;candles:Candle[]};
export type SupportedInterval=5|15|60|240;
const SUPPORTED_INTERVALS=new Set<number>([5,15,60,240]);
const twelveInterval=(minutes:SupportedInterval)=>({5:'5min',15:'15min',60:'1h',240:'4h'} as const)[minutes];

export function intervalLabel(minutes:number){return minutes===5?'M5':minutes===15?'M15':minutes===60?'H1':minutes===240?'H4':String(minutes)+'m';}

export function validateCandles(rows:Candle[],intervalMs:number,now=Date.now(),minimum=3,requireContinuous=true):Candle[]{
  if(!Number.isInteger(intervalMs)||intervalMs<=0)throw new Error('INVALID_INTERVAL');
  if(rows.some(c=>![c.time,c.open,c.high,c.low,c.close].every(Number.isFinite)||c.time<0||c.time>now+5000||c.time%intervalMs!==0||Math.min(c.open,c.high,c.low,c.close)<=0||c.high<Math.max(c.open,c.close,c.low)||c.low>Math.min(c.open,c.close,c.high)))throw new Error('INVALID_CANDLE');
  const closed=rows.filter(c=>c.time+intervalMs<=now).sort((a,b)=>a.time-b.time);
  if(closed.length<minimum)throw new Error('INSUFFICIENT_CLOSED_CANDLES');
  for(let i=1;i<closed.length;i++){
    const gap=closed[i].time-closed[i-1].time;
    if(gap<=0||(requireContinuous&&gap!==intervalMs))throw new Error('CANDLE_GAP_OR_DUPLICATE');
  }
  const age=now-(closed.at(-1)!.time+intervalMs);
  if(age<0||age>intervalMs*2)throw new Error('STALE_CANDLES');
  return closed;
}

function parseKrakenRows(result:Record<string,unknown>){
  const candidates=Object.entries(result||{}).filter(([key,value])=>key!=='last'&&Array.isArray(value));
  if(candidates.length!==1)throw new Error('BTC_INSTRUMENT_UNVERIFIED');
  return {instrument:candidates[0][0],rows:candidates[0][1] as unknown[][]};
}

export async function acquireCandles(symbol:string,intervalMinutes:SupportedInterval=5,minimum=3,requireContinuous=true):Promise<CandlePack>{
  if(!SUPPORTED_INTERVALS.has(intervalMinutes))throw new Error('UNSUPPORTED_INTERVAL');
  const observedAt=Date.now(),intervalMs=intervalMinutes*60_000;
  if(symbol==='BTCUSD'){
    const r=await fetch('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval='+intervalMinutes,{signal:AbortSignal.timeout(12000)});
    if(!r.ok)throw new Error('BTC_CANDLES_UNAVAILABLE');
    const body=await r.json();
    if(body.error?.length||!body.result)throw new Error('BTC_INSTRUMENT_UNVERIFIED');
    const parsed=parseKrakenRows(body.result);
    const mapped=parsed.rows.slice(0,-1).map(v=>({time:Number(v[0])*1000,open:Number(v[1]),high:Number(v[2]),low:Number(v[3]),close:Number(v[4])}));
    const candles=validateCandles(mapped,intervalMs,observedAt,minimum,requireContinuous);
    return {symbol,provider:'Kraken',providerInstrument:parsed.instrument,intervalMs,intervalMinutes,observedAt,candles};
  }
  if(symbol==='XAUUSD'){
    if(!process.env.TWELVE_DATA_API_KEY)throw new Error('GOLD_CANDLES_UNCONFIGURED');
    const query=new URLSearchParams({symbol:'XAU/USD',interval:twelveInterval(intervalMinutes),outputsize:String(Math.max(120,minimum+20)),timezone:'UTC',apikey:process.env.TWELVE_DATA_API_KEY});
    const r=await fetch('https://api.twelvedata.com/time_series?'+query,{signal:AbortSignal.timeout(12000)});
    if(!r.ok)throw new Error('GOLD_CANDLES_UNAVAILABLE');
    const body=await r.json();
    if(body.meta?.symbol!=='XAU/USD'||!Array.isArray(body.values))throw new Error('GOLD_INSTRUMENT_UNVERIFIED');
    const mapped=body.values.map((v:any)=>({time:Date.parse(String(v.datetime).replace(' ','T')+'Z'),open:Number(v.open),high:Number(v.high),low:Number(v.low),close:Number(v.close)})).reverse();
    const candles=validateCandles(mapped,intervalMs,observedAt,minimum,requireContinuous);
    return {symbol,provider:'Twelve Data',providerInstrument:'XAU/USD',intervalMs,intervalMinutes,observedAt,candles};
  }
  throw new Error('EXACT_INSTRUMENT_UNSUPPORTED');
}
