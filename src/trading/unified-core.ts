/**
 * Quantum Nexus unified trading core.
 * Decision-only: this module cannot submit broker orders or grant LIVE authority.
 * Callers must load durable daily state and persist new lockouts before treating them as authoritative.
 */
export type MarketInstrument = 'XAUUSD' | 'BTCUSD';
export type EvidenceState = 'VERIFIED' | 'UNAVAILABLE' | 'DEGRADED' | 'UNKNOWN';
export type ScenarioDirection = 'BUY' | 'SELL' | 'NEUTRAL';
export interface AstraScenario {
  instrument: MarketInstrument; direction: ScenarioDirection;
  status: 'READY' | 'QUALIFIED' | 'WATCH' | 'WAIT' | 'BLOCKED';
  entry: number | null; stopLoss: number | null; takeProfit: number | null;
  readinessScore: number; closedCandleEvidence: EvidenceState; priceEvidence: EvidenceState;
  sourceTimestamp: string | null; contradictions: string[];
}
export interface DailyProtectionSnapshot {
  /** Broker/account-local trading date, formatted YYYY-MM-DD. */
  dateKey: string; startingEquity: number; currentEquity: number;
  lockoutPersisted: boolean; lockoutReason: string | null;
  persistenceState: 'VERIFIED' | 'UNAVAILABLE' | 'UNKNOWN';
}
export interface UnifiedTradingConfig {
  dailyObjectivePct: number; dailyLossLimitPct: number; minimumReadinessScore: number;
  minimumRewardRisk: number; demoSignalQualificationEnabled: boolean;
}
export interface UnifiedDecision {
  instrument: MarketInstrument; decision: 'QUALIFIED_FOR_DEMO_REVIEW' | 'WATCH' | 'BLOCKED';
  reasons: string[]; dailyPnl: number | null; objectiveAmount: number | null; lossLimitAmount: number | null;
  lockoutRequired: boolean; lockoutReason: string | null; requiresDurableWrite: boolean;
  executionAuthority: 'NONE'; liveTrading: 'BLOCKED';
}
export const DEFAULT_UNIFIED_CONFIG: Readonly<UnifiedTradingConfig> = Object.freeze({
  dailyObjectivePct: 0.005, dailyLossLimitPct: 0.02, minimumReadinessScore: 80,
  minimumRewardRisk: 1.5, demoSignalQualificationEnabled: false,
});
function finitePositive(value: number): boolean { return Number.isFinite(value) && value > 0; }
function rewardRisk(s: AstraScenario): number | null {
  const {entry, stopLoss, takeProfit, direction} = s;
  if (entry === null || stopLoss === null || takeProfit === null) return null;
  if (![entry, stopLoss, takeProfit].every(Number.isFinite)) return null;
  const risk = direction === 'BUY' ? entry - stopLoss : stopLoss - entry;
  const reward = direction === 'BUY' ? takeProfit - entry : entry - takeProfit;
  if (direction === 'NEUTRAL' || risk <= 0 || reward <= 0) return null;
  return reward / risk;
}
/** Pure, deterministic, fail-closed orchestration of ASTRA + Opportunity Hunter + daily protection. */
export function evaluateUnifiedTradingDecision(
  scenario: AstraScenario, daily: DailyProtectionSnapshot,
  config: UnifiedTradingConfig = DEFAULT_UNIFIED_CONFIG,
): UnifiedDecision {
  const reasons: string[] = [];
  const validEquity = finitePositive(daily.startingEquity) && finitePositive(daily.currentEquity);
  const dailyPnl = validEquity ? daily.currentEquity - daily.startingEquity : null;
  const objectiveAmount = finitePositive(daily.startingEquity) ? daily.startingEquity * config.dailyObjectivePct : null;
  const lossLimitAmount = finitePositive(daily.startingEquity) ? daily.startingEquity * config.dailyLossLimitPct : null;
  let lockoutReason: string | null = daily.lockoutReason;
  let lockoutRequired = Boolean(daily.lockoutPersisted && daily.lockoutReason);
  let requiresDurableWrite = false;
  if (!validEquity) reasons.push('DAILY_EQUITY_INVALID');
  if (daily.persistenceState !== 'VERIFIED') reasons.push('DAILY_STATE_NOT_VERIFIED');
  if (validEquity && dailyPnl !== null && objectiveAmount !== null && dailyPnl >= objectiveAmount) {
    lockoutRequired = true; lockoutReason = 'DAILY_OBJECTIVE_REACHED'; reasons.push('DAILY_OBJECTIVE_REACHED');
  } else if (validEquity && dailyPnl !== null && lossLimitAmount !== null && dailyPnl <= -lossLimitAmount) {
    lockoutRequired = true; lockoutReason = 'DAILY_LOSS_LIMIT_REACHED'; reasons.push('DAILY_LOSS_LIMIT_REACHED');
  }
  if (lockoutRequired && !daily.lockoutPersisted) { requiresDurableWrite = true; reasons.push('LOCKOUT_WRITE_REQUIRED'); }
  else if (daily.lockoutPersisted && daily.lockoutReason) reasons.push('DAILY_LOCKOUT_ACTIVE');
  if (scenario.instrument !== 'XAUUSD') reasons.push('INSTRUMENT_ISOLATED_RESEARCH_ONLY');
  if (scenario.direction === 'NEUTRAL') reasons.push('NO_DIRECTIONAL_SETUP');
  if (!['READY', 'QUALIFIED'].includes(scenario.status)) reasons.push('SCENARIO_NOT_READY');
  if (scenario.closedCandleEvidence !== 'VERIFIED') reasons.push('CLOSED_CANDLE_EVIDENCE_NOT_VERIFIED');
  if (scenario.priceEvidence !== 'VERIFIED') reasons.push('PRICE_EVIDENCE_NOT_VERIFIED');
  if (!scenario.sourceTimestamp || !Number.isFinite(Date.parse(scenario.sourceTimestamp))) reasons.push('SOURCE_TIMESTAMP_INVALID');
  if (!Number.isFinite(scenario.readinessScore) || scenario.readinessScore < config.minimumReadinessScore) reasons.push('READINESS_BELOW_THRESHOLD');
  if (scenario.contradictions.length > 0) reasons.push('UNRESOLVED_CONTRADICTIONS');
  const rr = rewardRisk(scenario);
  if (rr === null || rr < config.minimumRewardRisk) reasons.push('REWARD_RISK_INVALID_OR_TOO_LOW');
  if (lockoutRequired) reasons.push('NEW_QUALIFICATION_BLOCKED_BY_DAILY_LOCKOUT');
  if (!config.demoSignalQualificationEnabled) reasons.push('DEMO_QUALIFICATION_DISABLED_BY_DEFAULT');
  const blocking = reasons.length > 0;
  return {
    instrument: scenario.instrument,
    decision: blocking ? (scenario.status === 'WATCH' || scenario.status === 'WAIT' ? 'WATCH' : 'BLOCKED') : 'QUALIFIED_FOR_DEMO_REVIEW',
    reasons: [...new Set(reasons)], dailyPnl, objectiveAmount, lossLimitAmount, lockoutRequired, lockoutReason,
    requiresDurableWrite, executionAuthority: 'NONE', liveTrading: 'BLOCKED',
  };
}
