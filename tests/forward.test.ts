import test from 'node:test';import assert from 'node:assert/strict';
import {validateCandles,type CandlePack} from '../server/candles.ts';
import {observePlan,summarizeObservations,type Plan} from '../server/forward.ts';
// Isolated safety fixtures; not production market data or performance samples.
const step=300000,now=step*10;
const c=(n:number,low=99,high=101)=>({time:n*step,open:100,close:100,low,high});
const plan:Plan={symbol:'TEST',direction:'BUY',entryLow:100,entryHigh:100,stop:95,target:110,createdAt:step,expiresAt:step*20};
const pack=(candles:any[]):CandlePack=>({symbol:'TEST',provider:'TEST_FIXTURE',providerInstrument:'TEST',intervalMs:step,observedAt:now,candles});
test('candle gate removes open bars and rejects gaps, stale data, bad OHLC',()=>{
 assert.equal(validateCandles([c(7),c(8),c(9),c(10)],step,now).length,3);
 assert.throws(()=>validateCandles([c(6),c(8),c(9)],step,now));
 assert.throws(()=>validateCandles([c(0),c(1),c(2)],step,now));
 assert.throws(()=>validateCandles([c(7),c(8),c(9,105,90)],step,now));
});
test('entry and terminal in one candle are ambiguous',()=>{assert.equal(observePlan(plan,pack([c(0),c(1,94,111)]),now).state,'AMBIGUOUS');});
test('later target touch is recorded without inferring profit',()=>{
 const r=observePlan(plan,pack([c(0),c(1),c(2,99,105),c(3,99,111)]),now);assert.equal(r.state,'TARGET_TOUCHED');assert.equal(r.favorableR,1);
 const s=summarizeObservations([r]);assert.equal(s.winRate,null);assert.equal(s.expectancy,null);
});
test('history missing the observation start blocks classification',()=>{assert.equal(observePlan(plan,pack([c(3),c(4),c(5)]),now).state,'DATA_GAP');});
test('pre-registration candle cannot trigger setup',()=>{
 const r=observePlan({...plan,createdAt:step+1},pack([c(0),c(1,94,111),{...c(2),open:105,close:105,low:104,high:106}]),now);assert.equal(r.state,'WATCH');
});
test('exact instrument, geometry and RR are mandatory',()=>{
 assert.throws(()=>observePlan(plan,{...pack([c(0)]),symbol:'OTHER'},now));
 assert.throws(()=>observePlan({...plan,stop:101},pack([]),now));
 assert.throws(()=>observePlan({...plan,target:102},pack([]),now));
});
