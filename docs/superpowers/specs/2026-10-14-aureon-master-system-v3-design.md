# AUREON Master System V3 — Design Specification

**Status:** Owner-approved for implementation planning on 2026-10-14; implementation plan awaits owner review  
**Date:** 2026-10-14  
**Repository:** jerryllee421-lab/aureon-omega  
**Proposed work branch:** design/aureon-master-system-v3

## 1. Goal

Create one dependable Windows .cmd entry point for AUREON development that coordinates local MQL5 build validation, deterministic cache preparation, isolated native MT5 Strategy Tester runs, evidence collection, and toolchain diagnostics. It must use installed development skills and connected GitHub/Vercel/Supabase tools appropriately, while avoiding duplicate CI implementations and never confusing compile success with trading-strategy validation.

The launcher is an orchestration and evidence system, not a trading agent. It must not connect to a user account, submit live orders, attach or enable an EA on an ordinary chart, or change the production web app as a side effect of local QA.

## 2. Evidence and current baseline

The following are observed in current repository configuration or owner-supplied console evidence:

- The repository README describes AUREON Ω as an analysis-only production web workspace with zero broker-order execution. The documented production stack is React/TypeScript/Vite on Vercel, AI through Vercel AI Gateway/OIDC, and privileged database calls through Supabase Edge Functions/OIDC.
- .github/workflows/ci.yml runs Node install, npm test, npm run build, and research Python syntax validation on pushes to main and pull requests.
- .circleci/config.yml defines a Node verification job and an opt-in full Gold research job with pinned research inputs and artifact packaging.
- The owner’s 2026-10-14 native compile report compile-20261014-105645/compile-report.json reported all four FVG_Scalper variants as PASS with zero compiler errors, zero warnings, and source/EX5 hashes recorded.
- The owner’s master run master-system-development-20261014-125248 passed source invariants, matched that compile report, acquired and SHA-256-verified the locked 2026 XAUUSD history file via a VSS snapshot, verified XAUUSD M1 history for 2024–2026, verified all 13 requested monthly real-tick files (202510–202610), and staged the four EX5 artifacts.
- That run started the first isolated native tester process, which exited with code -1000012353 without creating the expected HTML report. The current evidence does not establish the exit code’s cause. The associated tester diagnostics must be read before changing launch mechanics or retrying the batch.
- Earlier iterations exposed genuine launcher defects (wrong Expert path, use of Split-Path -Extension under Windows PowerShell 5.1, a Boolean parameter receiving a string, and fragile Base64 payload extraction). V3 must remove these failure patterns through explicit typed predicates, PowerShell 5.1-compatible APIs, a single anchored plain-text payload marker, and tests of the CMD-to-PowerShell handoff.

These observations establish current starting conditions only. They do not establish backtest performance, the presence of a valid native tester report, or demo/live profitability.

## 3. Design principles

1. **Evidence before claims.** A phase is PASS only when its specified artifacts and checks exist. Process exit code alone is insufficient.
2. **Fail closed.** Missing history, uncertain paths, source/report hash mismatches, absent reports, malformed metrics, or incomplete logs block downstream phases.
3. **Single entry point.** Deliver one self-contained .cmd file with a plain-text embedded PowerShell payload; no separate persistent helper scripts are required. Temporary files may be created in the run directory or %TEMP% and must be inventoried.
4. **PowerShell 5.1-first compatibility.** Avoid unsupported parameters, ambiguous Boolean binding, brittle quoting, and version-specific syntax. PowerShell 7 may be detected but is not required.
5. **Isolation.** Never close, reconfigure, log into, or manipulate the ordinary MT5 terminal. Use a distinct writable portable terminal directory with no copied common.ini, account profiles, saved logins, chart profiles, or ordinary-terminal MQL5\Profiles state.
6. **Read-only source control in validation mode.** The master validator may read source and EX5 files and copy the verified EX5 into the sandbox; it must not silently rewrite EA source or EX5 files. Code changes are made separately on a branch and then recompiled through a reviewable process.
7. **No blind retries.** On an unexpected terminal exit, gather and classify terminal and tester-agent logs once. Do not relaunch until the diagnostic gate identifies a concrete remediation or explicitly classifies the failure as transient with a bounded retry policy.
8. **Use existing systems.** GitHub Actions and CircleCI remain the canonical CI/research systems; do not duplicate those workflows in the local CMD. Use the connected GitHub MCP, installed Superpowers skills, and connected Vercel/Supabase tools during assistant-led development when relevant. The Windows CMD cannot assume that ChatGPT-side MCP connections are locally callable.
9. **Secrets remain secret.** Do not print access tokens, saved logins, refresh tokens, API keys, or full environment variable dumps. Auth checks may report present/absent and principal/repo scope without printing credential material.
10. **Demo-first / live blocked.** No live-trading enablement, live order submission, production strategy activation, or broker-execution claims are in scope.

## 4. Proposed architecture

### 4.1 Single-file launcher and payload handoff

The desktop entry point is a .cmd file containing:

- A small CMD bootstrap that sets the launcher path, starts Windows PowerShell 5.1 with -NoProfile -ExecutionPolicy Bypass, and returns the payload’s exit code.
- One unique marker line delimiting the plain-text PowerShell payload. Extraction must match the whole marker line, not a marker substring in the bootstrap command. The payload must be extracted as text, never Base64-decoded or executed from a mis-parsed command argument.
- Strict error handling and a final status summary. A crash should leave a diagnostic artifact and non-zero exit status.

A self-test mode will test extraction and parse the payload with the local PowerShell parser without running MT5, copying caches, or altering files.

### 4.2 Phase state machine

Every run emits a run ID and machine-readable phase states: NOT_RUN, RUNNING, PASS, BLOCKED, FAIL, or SKIPPED.

1. **BOOTSTRAP:** validate payload marker, PowerShell version, script path, filesystem encoding, and write access to the evidence root.
2. **TOOLCHAIN:** inventory PowerShell, Git, GitHub CLI, Node/npm, Python, .NET SDK, MetaEditor, and terminal versions. Separate required from optional tools. Do not install packages silently. When setup is requested, use exact vendor/package IDs, record the source/version, verify command versions after installation, and never authenticate or change scopes automatically.
3. **REPOSITORY_AND_CI:** record repository root, current branch, worktree/dirtiness, last commit, current CI references, and (when authenticated) status of existing GitHub checks. Never push or alter shared branches automatically. If credentials are absent, record UNAVAILABLE and continue only for tasks that do not require them.
4. **EA_INTEGRITY:** select the most recent eligible successful native compile report; verify report schema/status and that each expected source and EX5 hash matches. Check source invariants for the four supported variants. Report each test separately.
5. **PORTABLE_SANDBOX:** create or reuse a known sandbox with path canonicalization. Ensure it is not the ordinary terminal’s data path and contains no account/login/profile artifacts. Verify an existing portable terminal copy is complete before reuse.
6. **MINUTE_HISTORY_SYNC:** determine the actual cache source and target paths; copy the required XAUUSD history files into the sandbox. If a source is locked, try VSS snapshot only when the required Windows component and permissions are available. Record snapshot identity and file SHA-256. Never accept a size/timestamp-only duplicate as proof of file identity.
7. **TICK_HISTORY_SYNC:** enumerate the exact monthly TKC files required by the selected date range. For the current one-year test (2025-10-14 through 2026-10-13), verify months 202510 through 202610. For each file, record source/target paths, size, modification time, source hash and target hash. A cache gate passes only when every required month passes and the period/range mapping is internally consistent.
8. **STAGING:** copy verified EX5 files into the exact sandbox MQL5\Experts\<isolated-folder> location expected by the tester. Recompute hashes after staging and use the exact relative Expert INI field. Do not copy original chart profiles or user login state.
9. **TESTER_DIAGNOSTICS** (runs before first test and after any failure): discover the actual sandbox data root and collect terminal logs, tester logs, local-agent logs, journal logs, launch INI, process start/end/exit code, report search paths, staged Expert path and hash, and cache manifests. Redact credentials and tokens.
10. **NATIVE_STRATEGY_TESTER:** first execute only one preflight/diagnostic test invocation. Run the four EAs sequentially only when one complete valid report is produced and the associated logs show test completion. Use XAUUSD/M1, Model=4 (real ticks), specified date interval, USD 10,000 initial deposit, 1:100 leverage, source-default inputs, optimization disabled, local agents only, remote/cloud agents disabled, and visual mode off. These values must be written to each INI and included in evidence.
11. **REPORT_VALIDATION:** verify a report exists, is non-empty, parses as MT5 HTML, and corresponds to the expected EA/symbol/timeframe/date/model. Collect available metrics (net profit, total trades, profit factor, drawdown, recovery, equity balance, history/modeling indicators). Missing or contradictory metrics remain UNKNOWN; do not guess, infer, or turn absent values into zero. Keep the raw report unchanged and hash it.
12. **FINAL_EVIDENCE:** emit a summary JSON, a human-readable log, a per-variant manifest, all tester INI/log/report paths, cache verification manifest, source/EX5/report hashes, error classifications and explicit unsupported/unknown fields.

### 4.3 Failure classifier for current tester issue

For the current observed exit code -1000012353, V3 must not infer a root cause from the code alone. It must capture the actual sandbox’s:

- logs\YYYYMMDD.log and MQL5\Logs\YYYYMMDD.log;
- Tester\logs\YYYYMMDD.log, if present;
- all relevant Tester\Agent-*\logs outputs and any per-agent tester journals;
- generated .ini, staged EX5 existence and hashes, local-agent configuration and report search paths;
- process command line, start/end times, exit code, and a bounded Windows Application Event Log query when available.

It then classifies into a known reason only when a specific log signature or missing precondition supports that classification. Otherwise the state is UNKNOWN_BLOCKED, with the collected bundle and no automatic retry. This phase is the next immediate engineering target.

### 4.4 Evidence layout

Each run uses a unique directory under qa\artifacts\master-system-development-<timestamp>\ with at least:

- master-system-log.txt
- master-system-summary.json
- toolchain-inventory.json
- compile-evidence.json
- cache-manifest.json
- tester-configs\*.ini
- diagnostics-<EA>\ with relevant terminal/tester/agent log excerpts
- reports\<EA>.htm and a report hash/metrics record when available
- manifest.sha256 for files generated by the run

Logs should be append-only within a run folder. A new run must not overwrite prior evidence.

## 5. Development skills, connectors, MCP and CLI policy

### Assistant-side engineering workflow

- Use installed Superpowers skills in sequence: brainstorming/design for architecture; systematic-debugging for failures; writing-plans after the spec is approved; TDD for bug fixes; verification-before-completion before any success claim; code review before merge.
- Use the GitHub connector/MCP for repository inspection, feature branches, CI logs and evidence checks. Keep source work off main until reviewed.
- Use CircleCI through its existing configuration and artifacts; a CircleCI-specific plugin was not found in the current plugin search.
- Use Vercel skills/connectors for deployment and AI Gateway investigations only when the web application is in scope. Use Supabase skills/connectors for database/security work only when required. Do not connect these cloud systems to local trading execution.
- The plugin search showed GitHub and Vercel as already installed/available and Superpowers already installed. Do not attempt to reinstall installed plugins.

### Local CLI inventory and optional setup

Required to validate native EA builds: Windows PowerShell 5.1, MetaEditor, the expected QA project files, and write access to the evidence directory.

Recommended for wider development automation: Git, GitHub CLI (gh), Node.js 22.18+, npm, Python 3.13+, and .NET SDK for cTrader Cloud source. Vercel and Supabase CLIs are optional and only useful for corresponding application tasks.

The CLI setup stage must first inventory tools, then report a proposed install list with exact package IDs, publishers, versions, scope and source. Missing developer tools may be installed only from trusted vendor/package sources under the owner-approved setup path; if elevation, login or changed account scopes are required, stop and request the Windows/User interaction that is technically necessary. Never save tokens into the CMD, repo, logs or evidence. CLI authentication checks must not print credentials.

## 6. Safety boundaries

- Do not close, log off, relogin, or modify the normal MT5 process, profile, login settings, chart attachments or EA inputs.
- Never reuse the normal MT5 data directory as the portable sandbox.
- No broker-account connection, broker API, cTrader Open API, or account connector is initiated by the tester orchestrator. The isolated terminal must block before testing if logs indicate that any broker account was authenticated or attached.
- AllowLiveTrading=0, DLL import off, optimizer off, remote/cloud agents off, and no copied account credentials are mandatory gate conditions.
- If there is any ambiguity whether the launched terminal is the intended isolated instance, stop.
- Inspect isolated terminal/tester logs for account authorization, broker login, or connection to a user trading account. If any appears, mark SECURITY_BLOCKED, do not launch subsequent tests, and preserve the logs. Never close or modify the ordinary terminal.
- Do not edit .mq5/.ex5 files as part of cache repair or test execution. Source changes must have an explicit patch, backup, compile, hash verification, and rollback path in a distinct development step.
- No performance goal may override correctness, data-integrity, account-isolation or fail-closed gates.

## 7. Acceptance criteria

### Bootstrap and toolchain

- The self-test can extract and parse the embedded payload under Windows PowerShell 5.1 without evaluating CMD syntax as PowerShell.
- A unit/regression test covers the historical marker-substring failure and whole-line marker extraction.
- Boolean gate helpers reject strings; each call passes an explicit Boolean expression.
- The toolchain inventory completes with all checks individually PASS, MISSING, UNAVAILABLE, or BLOCKED; no tokens are printed.

### Build/source integrity

- Exactly four current variants are evaluated.
- Source and EX5 hashes match the same eligible successful native compile report, with zero errors/warnings.
- All expected full-copy guards, dynamic array series settings and closed-bar selectors are asserted explicitly.
- Source files are unchanged by the validation-only mode.

### Isolation/cache

- The ordinary terminal remains running and untouched before/during/after an isolated run.
- The portable sandbox path is distinct from all identified normal-terminal data roots.
- No account/profile/login files are copied.
- Source and target SHA-256 match for every required HCC/TKC file; all 13 test-month TKC files are verified.
- A file lock that cannot be resolved via consistent snapshot or a hash-verified duplicate blocks the run.
- Logs verify no authenticated user trading account or broker session was established in the isolated environment; otherwise the run is SECURITY_BLOCKED.

### Tester/report

- A single-variant pilot completes before the four-test batch starts.
- Tester success requires a non-empty valid report and matching tester completion logs; process exit code alone never counts as success.
- On failure, the diagnostic directory includes the launch INI, exact sandbox data root, process status, terminal log, tester log, local-agent logs where present, staged EX5 hash/path, report search results and reason classification.
- Unknown failures stop without blind retry or test-batch continuation.
- Four-variant run summary preserves per-variant reports and metrics. Missing performance metrics remain null/unknown.

### Delivery/security

- One .cmd is the primary entry point; evidence files are generated into unique run folders.
- Existing GitHub Actions/CircleCI workflows remain the canonical remote CI/research paths; no duplicate workflow is introduced without a measured need.
- No commits to main, automatic deployment, account changes, broker connection, order placement or live trading are performed by the local tester workflow.

## 8. Out of scope

- Editing or optimizing the trading strategy to improve backtest results.
- Certifying profitability based on compilation or a single historical backtest.
- Live trading, live broker login, or live order execution.
- Replacing GitHub Actions, CircleCI, Vercel, Supabase or their current authentication architecture.
- Installing every available plugin or MCP server regardless of task fit.

## 9. Rollout approach after spec approval

1. Write the task-level implementation plan and agree the execution method.
2. Create an isolated development branch/workspace and a progress ledger.
3. First add tests for the payload parser, phase-state model, and failure-report collection without launching MT5.
4. Fix the current NATIVE_STRATEGY_TESTER diagnosis so it identifies the actual cause of -1000012353 from the sandbox logs before changing tester invocation again.
5. Implement and verify individual phases in order; do not rerun a year-long tick campaign until a single-variant pilot produces a valid report.
6. Run repository CI and all locally safe tests; use the available connectors for CI/deployment status as relevant.
7. Request code review and present evidence and remaining unknowns before any merge or test campaign expansion.
