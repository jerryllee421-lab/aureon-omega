export async function referenceQuote(symbol: string) {
  const observedAt = new Date().toISOString();
  if (symbol === 'BTCUSD') {
    const r = await fetch('https://api.coinbase.com/v2/prices/BTC-USD/spot', { signal: AbortSignal.timeout(8000) });
    if (!r.ok) throw new Error('BTC_PROVIDER_UNAVAILABLE');
    const body = await r.json(); const price = Number(body.data?.amount);
    if (body.data?.base !== 'BTC' || body.data?.currency !== 'USD' || !Number.isFinite(price) || price <= 0) throw new Error('BTC_PROVIDER_INVALID');
    return { symbol: 'BTCUSD', providerInstrument: 'BTC-USD', provider: 'Coinbase', price, observedAt, sourceTimestamp: null, authority: 'REFERENCE_ONLY', reason: 'Spot reference has no source timestamp or broker bid/ask.', executionEligible: false };
  }
  if (symbol === 'XAUUSD') {
    if (!process.env.TWELVE_DATA_API_KEY) return { symbol, price: null, authority: 'UNAVAILABLE', reason: 'Gold provider key is not configured.', executionEligible: false };
    const query = new URLSearchParams({ symbol:'XAU/USD', interval:'1min', outputsize:'2', timezone:'UTC', apikey:process.env.TWELVE_DATA_API_KEY });
    const r = await fetch('https://api.twelvedata.com/time_series?' + query, { signal: AbortSignal.timeout(8000) });
    if (!r.ok) throw new Error('GOLD_PROVIDER_UNAVAILABLE');
    const body = await r.json(); const candle = body.values?.[0]; const price = Number(candle?.close);
    const timestamp = Date.parse(String(candle?.datetime || '').replace(' ', 'T') + 'Z');
    if (body.meta?.symbol !== 'XAU/USD' || !Number.isFinite(price) || price <= 0 || !Number.isFinite(timestamp)) throw new Error('GOLD_PROVIDER_INVALID');
    const age = Date.now() - timestamp;
    return { symbol, providerInstrument:'XAU/USD', provider:'Twelve Data', price, observedAt, sourceTimestamp:new Date(timestamp).toISOString(), authority:age >= 0 && age < 120000 ? 'REFERENCE_ONLY' : 'STALE', reason:'Candle reference; no broker bid/ask or guaranteed closed-candle trigger.', executionEligible:false };
  }
  return { symbol, price:null, authority:'UNAVAILABLE', reason:'No verified adapter for this exact instrument.', executionEligible:false };
}
