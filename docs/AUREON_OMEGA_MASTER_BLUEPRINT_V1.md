# QUANTUM NEXUS AUREON Ω — Authoritative Master Blueprint

**Document version:** 1.0  
**Status:** Approved project governance baseline  
**Primary objective:** Prove a robust XAUUSD strategy before major platform expansion  
**Execution boundary:** Research and controlled MT5 DEMO execution only; LIVE trading is blocked.

## 1. Locked decisions

1. Strategy validation is the project's first priority.
2. GoldQUANTUM V6 is a candidate under evaluation, not an automatically approved winner.
3. V2.12 remains a preserved frozen benchmark/control.
4. V6 and V2.12 compete under the same validation protocol; evidence determines the champion.
5. Use MT5 **Every Tick Based on Real Ticks** wherever native broker tick data is available and suitable.
6. DEMO-only execution. LIVE authorization is out of scope and remains blocked.
7. Preserve baseline source, settings, data provenance, tester reports, and logs. Any repair or optimization gets a separate version.
8. Reports must separate verified facts, user-reported results, hypotheses, and unknowns.

## 2. Current evidence status

- **User-reported:** GoldQUANTUM V6 produced a result of R7.4 million during 2025.
- **Pending verification:** The reported 2025 result, starting balance/equity, deposit currency, inputs, costs, drawdown, and exact tester configuration.
- **In progress / not independently observed here:** A real-tick test spanning 2025 and including 2026.
- **Preservation requirement:** Do not overwrite V2.12 or the exact V6 candidate used by a running test.
- **Not yet established:** Actual compilation status for the exact source, independent reproducibility, 2026 results, out-of-sample robustness, and live-market profitability.

No performance number is considered independently verified until its source report and test configuration are inspected.

## 3. System architecture and order of priority

### Layer 1 — Data truth
- Record broker, symbol specification, server timezone, test dates, tick model, data coverage, spread and commission assumptions.
- Check timestamp integrity, missing intervals, duplicate/out-of-order records, bid/ask consistency and spread anomalies.
- Prefer native MT5 real ticks for the benchmark tests. Do not silently substitute generated ticks or bar-based proxies.
- Hash and version the datasets and record their source.

### Layer 2 — Frozen strategy candidates
- Preserve exact V6 source and its input set.
- Preserve V2.12 source, configuration and historical benchmark artifacts.
- Do not edit either frozen candidate while a test is running.
- Any code repair or optimization must use a new version and a documented change log.

### Layer 3 — Fair validation harness
Run each candidate with matched broker/symbol assumptions, deposit currency and starting balance, date windows, tick mode, costs, execution settings and risk constraints wherever technically possible. Record unavoidable differences.

Required evaluation windows:
1. 2025 separately, to reproduce the reported result.
2. 2026 separately, to inspect the additional period.
3. The complete shared period, for aggregate behaviour.
4. Subsequent forward-demo data, once available.

Do not use a single combined result to conceal a weak sub-period.

### Layer 4 — Strategy metrics
Capture at minimum:
- Net profit and return relative to starting equity.
- Profit factor and expected payoff per trade.
- Maximum balance drawdown and maximum equity drawdown, absolute and relative.
- Recovery factor and Sharpe ratio where calculable and methodologically appropriate.
- Trade count, win rate, average win/loss, long/short breakdown and exposure.
- Commission, swap, spread, slippage assumptions and sensitivity.
- Results by month, session and meaningful market regime.
- Concentration of profits in a small number of trades or days.
- Order rejection, invalid-stop, margin and other execution error counts.

Profit alone is not a ranking criterion. A candidate with greater profit but unacceptable drawdown, fragile costs, or unreliable execution cannot be crowned champion.

### Layer 5 — Robustness and overfitting controls
- Keep baseline tests separate from optimization runs.
- Use chronological out-of-sample / walk-forward evaluation where the available data supports it.
- Do not repeatedly tune against the final holdout period.
- Run controlled spread/slippage and cost stress tests.
- Check parameter stability and performance across months and market regimes.
- Keep a full experiment ledger: hypothesis, changed variables, run ID, source version, inputs, result, and decision.

### Layer 6 — Risk kernel
Risk controls must be independent of AI recommendations and strategy signals:
- Hard DEMO account/symbol allowlist.
- Explicit per-trade risk and aggregate exposure caps.
- Daily loss and equity drawdown locks with persistent state.
- Protective position management continues when new entries are blocked.
- Validate volume step/min/max, tick size/value, stop distance, margin and trade permissions.
- Correct direction-aware management for both buys and sells where enabled.
- Validate pending-order SL/TP against the actual pending entry price.
- Check all trade retcodes and reconcile local state against broker-confirmed orders, deals and positions.
- Fail closed on missing, stale, contradictory or invalid critical data.

Exact numerical risk thresholds must be documented in the tested configuration; do not infer or silently change them.

### Layer 7 — Demo forward validation
- Use the designated MT5 DEMO account and XAUUSD broker symbol only after explicit preflight.
- Start with execution and protection verification before increasing exposure.
- Test restart recovery, daily-lock persistence, duplicate-order prevention, order rejection handling, partial closes and journal reconciliation.
- Compare forward-demo fills and costs with tester assumptions.
- Live trading remains blocked.

### Layer 8 — ASTRA and platform work
Only after strategy validation has produced credible evidence, expand ASTRA's research ranking, evidence ledger, decision explanations, dashboard and automation. ASTRA may summarize evidence and recommend WAIT / NO-TRADE; it must not bypass deterministic risk gates or independently authorize live orders.

## 4. Champion selection rule

V6 and V2.12 are evaluated using the same documented protocol. The champion is selected only after:
1. Source/configuration identity is confirmed.
2. Comparable real-tick test results are available.
3. Risk-adjusted metrics and drawdown are reviewed.
4. 2025 and 2026 sub-periods are reviewed separately.
5. Costs, robustness and execution defects are assessed.
6. Results are reproducible and the decision is recorded.

If the evidence is incomplete, contradictory or too weak, the decision is **NO WINNER / CONTINUE RESEARCH**. V2.12 remains the preserved control regardless of the outcome.

## 5. Implementation sequence and exit gates

### Phase 0 — Preserve and inventory
**Work:** Capture V6 and V2.12 source hashes, inputs, reports, symbol specification and data provenance.  
**Exit gate:** Both candidates and current test setup are identifiable and recoverable.

### Phase 1 — Finish current real-tick test
**Work:** Do not alter the running test candidate. Collect the full MT5 report, graph, inputs and journal/logs when complete.  
**Exit gate:** Test dates, modelling mode, data coverage, account currency, costs and headline metrics are documented.

### Phase 2 — Reproduce and compare
**Work:** Run separate 2025 and 2026 windows and matched comparison runs for V6 and V2.12 where data/configuration permits.  
**Exit gate:** Comparison matrix complete; differences in assumptions disclosed.

### Phase 3 — Diagnose
**Work:** Inspect source and reports for direction errors, risk sizing, position/pending-order management, repeated partial exits, state persistence, broker constraints, and performance concentration.  
**Exit gate:** Findings classified as confirmed defect, suspected defect, or no issue; each tied to evidence.

### Phase 4 — Build a separate hardened candidate
**Work:** Fix only justified defects in a separately named source/version. Preserve frozen inputs and source.  
**Exit gate:** Static review and MetaEditor compilation evidence recorded; no claim of successful compilation without the actual result.

### Phase 5 — Regression and robustness
**Work:** Repeat baseline tests, cost sensitivity, chronological out-of-sample checks and monthly/regime analysis.  
**Exit gate:** No unexplained regression; all thresholds and selection rules are documented.

### Phase 6 — Controlled demo
**Work:** Execute a limited demo-only trial with persistent risk controls, broker reconciliation and audit logs.  
**Exit gate:** Forward-demo evidence meets predeclared operational and risk criteria.

### Phase 7 — ASTRA/platform integration
**Work:** Automate evidence ingestion, candidate comparisons, reports and dashboard status.  
**Exit gate:** Every displayed claim traces to a report or source; unknown states are explicit.

## 6. Reproducibility record

Every test record must include:
- Unique run ID and timestamp.
- EA name/version and source commit/hash.
- Exact input file/hash.
- Broker, account mode (DEMO), symbol and symbol specification.
- Deposit currency, starting balance/equity, leverage and account settings.
- Start/end dates and server-time interpretation.
- MT5 build, tester mode and tick-data source/coverage.
- Spread, commission, swap, slippage and execution assumptions.
- Report file(s), journal/logs, summary metrics and reviewer decision.

## 7. Reporting vocabulary

Use these labels consistently:
- **VERIFIED:** Supported by inspectable source/report/test evidence.
- **USER-REPORTED:** Supplied by the user but not independently checked.
- **IN PROGRESS:** Work is demonstrably underway.
- **UNKNOWN:** Evidence is not available.
- **BLOCKED:** A required gate has failed or remains unmet.
- **PASSED:** A specific named test passed; this does not imply all project gates passed.

Never describe a source as compiled, a test as completed, a deployment as live, or a strategy as profitable unless the corresponding evidence is available.

## 8. Safety and preservation rules

- LIVE trading remains blocked.
- No secret, broker password or account credential is to be committed to Git.
- No running test candidate is modified in place.
- Frozen V2.12 artifacts remain read-only controls.
- Generated ticks, synthetic data and proxy data must never be labelled native real ticks.
- A profitable backtest does not guarantee future results.
- If required data or execution state is unavailable, do not open new trades.

## 9. Immediate next actions

1. Finish the currently running Every Tick Based on Real Ticks test and preserve its full artifacts.
2. Reproduce V6's reported 2025 result, then evaluate 2026 independently.
3. Execute the same validation protocol for V2.12 and issue an evidence-based comparison report.
4. Only then finalize the defect list and implement a separate hardened candidate.
5. Keep all MT5 execution DEMO-only and LIVE blocked throughout these phases.
