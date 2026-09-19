export type ReferenceQuote={
  symbol:string;providerInstrument?:string;provider:string;price:number|null;bid?:number|null;ask?:number|null;
  spreadBps?:number|null;crossProviderDeviationBps?:number|null;observedAt:string;sourceTimestamp:string|null;
  authority:string;reason:string;executionEligible:false;providers?:string[];
};

const positive=(value:unknown)=>{const n=Number(value);return Number.isFinite(n)&&n>0?n:null;};
const bps=(a:number,b:number)=>Math.abs(a-b)/Math.max(Math.abs(b),Number.EPSILON)*10000;

export function assessBtcReferences(coinbaseSpot:number,krakenBid:number,krakenAsk:number,observedAt=new Date().toISOString()):ReferenceQuote{
  if(![coinbaseSpot,krakenBid,krakenAsk].every(n=>Number.isFinite(n)&&n>0)||krakenAsk<krakenBid)throw new Error('BTC_PROVIDER_INVALID');
  const midpoint=(krakenBid+krakenAsk)/2;
  const spreadBps=(krakenAsk-krakenBid)/midpoint*10000;
  const crossProviderDeviationBps=bps(coinbaseSpot,midpoint);
  const conflict=crossProviderDeviationBps>50;
  return {
    symbol:'BTCUSD',providerInstrument:'BTC-USD / XBTUSD',provider:'Coinbase + Kraken',
    providers:['Coinbase','Kraken'],price:midpoint,bid:krakenBid,ask:krakenAsk,spreadBps,crossProviderDeviationBps,
    observedAt,sourceTimestamp:null,authority:conflict?'REFERENCE_CONFLICT':'REFERENCE_CROSSCHECKED',
    reason:conflict
      ? 'Coinbase spot and Kraken midpoint differ by more than 50 bps; execution authority remains blocked.'
      : 'Coinbase spot is cross-checked against Kraken best bid/ask. Neither source is a broker execution feed and source timestamps are unavailable.',
    executionEligible:false,
  };
}

async function coinbaseBtc(){
  const r=await fetch('https://api.coinbase.com/v2/prices/BTC-USD/spot',{signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw new Error('COINBASE_UNAVAILABLE');
  const body=await r.json();const price=positive(body.data?.amount);
  if(body.data?.base!=='BTC'||body.data?.currency!=='USD'||price===null)throw new Error('COINBASE_INVALID');
  return price;
}

async function krakenBtc(){
  const r=await fetch('https://api.kraken.com/0/public/Ticker?pair=XBTUSD',{signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw new Error('KRAKEN_UNAVAILABLE');
  const body=await r.json();if(body.error?.length)throw new Error('KRAKEN_INVALID');
  const rows=Object.values(body.result||{}) as any[];
  if(rows.length!==1)throw new Error('KRAKEN_INSTRUMENT_UNVERIFIED');
  const bid=positive(rows[0]?.b?.[0]),ask=positive(rows[0]?.a?.[0]);
  if(bid===null||ask===null||ask<bid)throw new Error('KRAKEN_INVALID');
  return {bid,ask};
}

export async function referenceQuote(symbol:string):Promise<ReferenceQuote>{
  const observedAt=new Date().toISOString();
  if(symbol==='BTCUSD'){
    const [coinbase,kraken]=await Promise.allSettled([coinbaseBtc(),krakenBtc()]);
    if(coinbase.status==='fulfilled'&&kraken.status==='fulfilled')return assessBtcReferences(coinbase.value,kraken.value.bid,kraken.value.ask,observedAt);
    if(kraken.status==='fulfilled'){
      const midpoint=(kraken.value.bid+kraken.value.ask)/2;
      return {symbol,providerInstrument:'XBTUSD',provider:'Kraken',providers:['Kraken'],price:midpoint,bid:kraken.value.bid,ask:kraken.value.ask,
        spreadBps:(kraken.value.ask-kraken.value.bid)/midpoint*10000,crossProviderDeviationBps:null,observedAt,sourceTimestamp:null,
        authority:'REFERENCE_ONLY',reason:'Kraken best bid/ask available, but independent cross-provider confirmation is unavailable.',executionEligible:false};
    }
    if(coinbase.status==='fulfilled')return {symbol,providerInstrument:'BTC-USD',provider:'Coinbase',providers:['Coinbase'],price:coinbase.value,
      observedAt,sourceTimestamp:null,authority:'REFERENCE_ONLY',reason:'Coinbase spot reference available; Kraken cross-check is unavailable.',executionEligible:false};
    throw new Error('BTC_PROVIDERS_UNAVAILABLE');
  }
  if(symbol==='XAUUSD'){
    if(!process.env.TWELVE_DATA_API_KEY)return {symbol,provider:'Twelve Data',providerInstrument:'XAU/USD',price:null,observedAt,sourceTimestamp:null,authority:'UNAVAILABLE',reason:'Gold provider key is not configured.',executionEligible:false};
    const query=new URLSearchParams({symbol:'XAU/USD',interval:'1min',outputsize:'2',timezone:'UTC',apikey:process.env.TWELVE_DATA_API_KEY});
    const r=await fetch('https://api.twelvedata.com/time_series?'+query,{signal:AbortSignal.timeout(8000)});
    if(!r.ok)throw new Error('GOLD_PROVIDER_UNAVAILABLE');
    const body=await r.json();const candle=body.values?.[0];const price=positive(candle?.close);
    const timestamp=Date.parse(String(candle?.datetime||'').replace(' ','T')+'Z');
    if(body.meta?.symbol!=='XAU/USD'||price===null||!Number.isFinite(timestamp))throw new Error('GOLD_PROVIDER_INVALID');
    const age=Date.now()-timestamp;
    return {symbol,providerInstrument:'XAU/USD',provider:'Twelve Data',price,observedAt,sourceTimestamp:new Date(timestamp).toISOString(),
      authority:age>=0&&age<120000?'REFERENCE_ONLY':'STALE',
      reason:'Timestamped XAU/USD candle reference; no broker bid/ask or guaranteed execution trigger.',executionEligible:false};
  }
  return {symbol,provider:'UNAVAILABLE',price:null,observedAt,sourceTimestamp:null,authority:'UNAVAILABLE',reason:'No verified adapter for this exact instrument.',executionEligible:false};
}
