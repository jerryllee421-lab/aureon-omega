// Deterministic indicator fixtures only; these values are not market data or performance samples.
import test from 'node:test';import assert from 'node:assert/strict';
import {quantSnapshot,mtfAlignment,emaLatest,rsiLatest,atrLatest,adxLatest} from '../server/quant.ts';
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
