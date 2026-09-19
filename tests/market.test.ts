import test from 'node:test';import assert from 'node:assert/strict';import {assessBtcReferences} from '../server/market.ts';
test('BTC cross-provider reference keeps execution blocked and exposes divergence',()=>{
 const q=assessBtcReferences(100000,99990,100010,'2026-01-01T00:00:00.000Z');
 assert.equal(q.executionEligible,false);assert.equal(q.authority,'REFERENCE_CROSSCHECKED');assert.equal(q.price,100000);assert.equal(q.spreadBps,2);assert.equal(q.crossProviderDeviationBps,0);
});
test('large BTC provider disagreement is surfaced as a conflict',()=>{
 const q=assessBtcReferences(101000,99990,100010);assert.equal(q.authority,'REFERENCE_CONFLICT');assert.ok((q.crossProviderDeviationBps||0)>50);assert.equal(q.executionEligible,false);
});
