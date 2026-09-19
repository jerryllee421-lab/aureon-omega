// AI output is a hypothesis. Only exact numeric values extracted in the signed
// canonical chart evidence are eligible to appear as conditional plan levels.
export function numbers(value: unknown): number[] {
  const text = String(value ?? '').trim().replace(/(?<=\d),(?=\d{3}(?:\D|$))/g, '');
  if (!/^\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?$/.test(text)) return [];
  return text.split(/\s*[-–]\s*/).map(Number).filter(n => Number.isFinite(n) && n > 0);
}
export function harden(result: any, canonical: any) {
  const supported = new Set<number>();
  for (const chart of canonical.charts || []) {
    if (!chart.priceScaleVisible || chart.imageQuality === 'INVALID') continue;
    for (const values of Object.values(chart.levels || {})) {
      for (const value of Array.isArray(values) ? values : []) numbers(value).forEach(n => supported.add(n));
    }
    numbers(chart.currentPrice).forEach(n => supported.add(n));
  }
  for (const opportunity of result.opportunities || []) {
    opportunity.executable = false;
    if (opportunity.status === 'CONFIRMED') opportunity.status = 'FORMING';
    for (const field of ['entryZone','stopLoss','tp1','tp2','tp3']) {
      const parsed = numbers(opportunity[field]);
      if (!parsed.length || !parsed.every(n => supported.has(n))) opportunity[field] = null;
    }
    const entry = numbers(opportunity.entryZone), stop = numbers(opportunity.stopLoss)[0];
    for (const i of [1,2,3]) opportunity['rr' + i] = null;
    if (entry.length && stop) {
      const worst = opportunity.direction === 'BUY' ? Math.max(...entry) : Math.min(...entry);
      const risk = opportunity.direction === 'BUY' ? worst - stop : stop - worst;
      const near = opportunity.direction === 'BUY' ? Math.min(...entry) : Math.max(...entry);
      if (risk <= 0 || (opportunity.direction === 'BUY' ? stop >= near : stop <= near)) {
        opportunity.stopLoss = null;
      } else {
        let previousReward = 0;
        for (const i of [1,2,3]) {
          const target = numbers(opportunity['tp' + i])[0];
          const reward = opportunity.direction === 'BUY' ? target - worst : worst - target;
          if (!target || reward <= previousReward) opportunity['tp' + i] = null;
          else { opportunity['rr' + i] = '1:' + (reward / risk).toFixed(2); previousReward = reward; }
        }
      }
    }
    if (!opportunity.entryZone || !opportunity.stopLoss || !opportunity.tp1) opportunity.readinessScore = Math.min(opportunity.readinessScore, 55);
  }
  const symbols = [...new Set((canonical.charts || []).map((c: any) => String(c.symbol).toUpperCase().replace(/[^A-Z0-9]/g,'')).filter((s: string) => s && s !== 'UNKNOWN'))];
  if (symbols.length !== 1 || canonical.overallImageQuality === 'INVALID') {
    result.opportunities = []; result.limitations.push('Chart identity or image authority is unresolved. Upload legible charts of one exact instrument.');
  }
  const observedPrices = [...new Set((canonical.charts || []).flatMap((c: any) => c.priceScaleVisible ? numbers(c.currentPrice) : []))];
  result.currentPrice = { value: observedPrices.length === 1 ? String(observedPrices[0]) : null, authority: observedPrices.length === 1 ? 'OBSERVED' : 'UNKNOWN' };
  result.opportunities.sort((a: any,b: any) => b.readinessScore - a.readinessScore);
  result.readinessScore = result.opportunities[0]?.readinessScore || 0;
  result.decision = result.opportunities.length ? 'CONDITIONAL_SCENARIOS' : 'WAIT';
  result.setupState = result.opportunities.length ? 'FORMING' : 'INSUFFICIENT_DATA';
  result.tradePlan = Object.fromEntries(Object.keys(result.tradePlan).map(k => [k, null]));
  result.executionAuthority = 'BLOCKED';
  result.reasoningEffort = 'PROVIDER_DEFAULT';
  return result;
}
