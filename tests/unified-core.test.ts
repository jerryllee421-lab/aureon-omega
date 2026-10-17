import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_UNIFIED_CONFIG, evaluateUnifiedTradingDecision, type AstraScenario, type DailyProtectionSnapshot } from '../src/trading/unified-core.ts';
const scenario: AstraScenario = {
  instrument:'XAUUSD', direction:'BUY', status:'READY', entry:2700, stopLoss:2690, takeProfit:2720,
  readinessScore:92, closedCandleEvidence:'VERIFIED', priceEvidence:'VERIFIED',
  sourceTimestamp:'2026-10-17T12:00:00.000Z', contradictions:[],
};
const daily: DailyProtectionSnapshot = {
  dateKey:'2026-10-17', startingEquity:10000, currentEquity:10000, lockoutPersisted:false,
  lockoutReason:null, persistenceState:'VERIFIED',
};
test('default config cannot qualify and never grants execution authority', () => {
  const r=evaluateUnifiedTradingDecision(scenario,daily);
  assert.equal(DEFAULT_UNIFIED_CONFIG.demoSignalQualificationEnabled,false);
  assert.equal(r.executionAuthority,'NONE'); assert.equal(r.liveTrading,'BLOCKED'); assert.equal(r.decision,'BLOCKED');
});
test('0.5% daily objective requires durable lockout write', () => {
  const r=evaluateUnifiedTradingDecision(scenario,{...daily,currentEquity:10050},{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.objectiveAmount,50); assert.equal(r.lockoutReason,'DAILY_OBJECTIVE_REACHED');
  assert.equal(r.lockoutRequired,true); assert.equal(r.requiresDurableWrite,true);
});
test('daily loss limit is independent from the objective', () => {
  const r=evaluateUnifiedTradingDecision(scenario,{...daily,currentEquity:9800},{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.lossLimitAmount,200); assert.equal(r.lockoutReason,'DAILY_LOSS_LIMIT_REACHED'); assert.equal(r.lockoutRequired,true);
});
test('BTC remains isolated from XAUUSD workflow', () => {
  const r=evaluateUnifiedTradingDecision({...scenario,instrument:'BTCUSD'},daily,{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.decision,'BLOCKED'); assert.ok(r.reasons.includes('INSTRUMENT_ISOLATED_RESEARCH_ONLY'));
});
test('unverified market evidence fails closed', () => {
  const r=evaluateUnifiedTradingDecision({...scenario,priceEvidence:'UNAVAILABLE'},daily,{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.decision,'BLOCKED'); assert.ok(r.reasons.includes('PRICE_EVIDENCE_NOT_VERIFIED'));
});
test('persisted daily lockout blocks qualification', () => {
  const r=evaluateUnifiedTradingDecision(scenario,{...daily,lockoutPersisted:true,lockoutReason:'DAILY_OBJECTIVE_REACHED'},{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.lockoutRequired,true); assert.ok(r.reasons.includes('DAILY_LOCKOUT_ACTIVE')); assert.equal(r.decision,'BLOCKED');
});
test('invalid equity and contradictory evidence are blocked', () => {
  const r=evaluateUnifiedTradingDecision({...scenario,contradictions:['price mismatch']},{...daily,currentEquity:Number.NaN},{...DEFAULT_UNIFIED_CONFIG,demoSignalQualificationEnabled:true});
  assert.equal(r.decision,'BLOCKED'); assert.ok(r.reasons.includes('DAILY_EQUITY_INVALID')); assert.ok(r.reasons.includes('UNRESOLVED_CONTRADICTIONS'));
});
