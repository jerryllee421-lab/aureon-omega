// Deterministic indicator fixtures only; these values are not market data or performance samples.
import test from 'node:test';import assert from 'node:assert/strict';
import {quantSnapshot,mtfAlignment,emaLatest,rsiLatest,atrLatest,adxLatest} from '../server/quant.ts';
import {deriveMarketBrain} from '../server/marketBrain.ts';
import type {CandlePack} from '../server/candles.ts';

function trendPack(direction:1|-1):CandlePack{
 const intervalMs=300000,start=1735689600000,candles=[];
 for(let i=0;i<120;i++){const base=100+direction*i*0.5,open=base-direction*0.1,close=base,high=Math.max(open,close)+0.2,low=Math.min(open,close)-0.2;candles.push({time:start+i*intervalMs,open,high,low,close});}
 return {symbol:'TESTUSD',provider:'TEST_FIXTURE',providerInstrument:'TEST',intervalMs,intervalMinutes:5,observedAt:start+121*intervalMs,candles};
}
test('quant indicators are finite on sufficient deterministic history',()=>{
 const pack=trendPack(1),closes=pack.candles.map(c=>c.close);
 for(const v of [emaLatest(closes,20),rsiLatest(closes),atrLatest(pack.candles),adxLatest(pack.candles)])assert.ok(v!==null&&Number.isFinite(v));
});
test('uptrend context remains non-executable',()=>{
 const q=quantSnapshot(trendPack(1));assert.equal(q.bias,'UP');assert.equal(q.regime,'TREND_UP');assert.equal(q.executionEligible,false);assert.equal(q.authority,'CLOSED_CANDLE_REFERENCE');
});
test('downtrend context remains non-executable',()=>{
 const q=quantSnapshot(trendPack(-1));assert.equal(q.bias,'DOWN');assert.equal(q.regime,'TREND_DOWN');assert.equal(q.executionEligible,false);
});
test('MTF alignment requires broad agreement',()=>{
 assert.equal(mtfAlignment([{bias:'UP'},{bias:'UP'},{bias:'UP'},{bias:'NEUTRAL'}]).alignment,'BULLISH_ALIGNMENT');
 assert.equal(mtfAlignment([{bias:'UP'},{bias:'DOWN'},{bias:'UP'},{bias:'NEUTRAL'}]).alignment,'MIXED');
});

test('Market Brain routes state without granting execution authority',()=>{
 const frames=[
  {status:'READY',timeframe:'M5',intervalMinutes:5,bias:'UP',structure:'HH_HL',regime:'TREND_UP',adx14:26},
  {status:'READY',timeframe:'M15',intervalMinutes:15,bias:'UP',structure:'HH_HL',regime:'TREND_UP',adx14:28},
  {status:'READY',timeframe:'H1',intervalMinutes:60,bias:'UP',structure:'HH_HL',regime:'TREND_UP',adx14:24},
  {status:'READY',timeframe:'H4',intervalMinutes:240,bias:'NEUTRAL',structure:'MIXED',regime:'RANGE_OR_TRANSITION',adx14:18},
 ];
 const brain=deriveMarketBrain('XAUUSD',frames,{focusWindow:'LONDON_SESSION',london:{active:true},newYork:{active:false}});
 assert.equal(brain.executionEligible,false);
 assert.equal(brain.marketState.directionalState,'BULLISH_LEAN');
 assert.equal(brain.strategyRouter.preferred,'QEDGE_02_TREND_PULLBACK');
 assert.equal(brain.dataAuthority.volumeProfile,'UNAVAILABLE');
 assert.equal(brain.dataAuthority.cvd,'UNAVAILABLE');
 assert.equal(brain.dataAuthority.gex,'UNAVAILABLE');
});
