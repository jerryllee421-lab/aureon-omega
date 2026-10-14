# AUREON Master System V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build one dependable Windows CMD entry point that validates AUREON's local MQL5 compile evidence, safely prepares an isolated MT5 testing environment, diagnoses the existing tester failure before any retry, and produces verifiable per-run evidence.

**Architecture:** Keep the production app and existing remote CI unchanged. Implement a single self-contained CMD launcher with an embedded plain-text PowerShell 5.1 payload, explicit phase state and fail-closed gates, and an isolated portable MT5 sandbox. Build the diagnostics-only path first; only permit a one-variant native tester pilot after account isolation, caches, EX5 hashes, configuration and logs pass their gates.

**Tech Stack:** Windows CMD, Windows PowerShell 5.1, Node.js built-in test runner and TypeScript tests already used by the repository, MetaEditor/MT5 Strategy Tester, GitHub connector/MCP, existing GitHub Actions and CircleCI.

**Spec:** docs/superpowers/specs/2026-10-14-aureon-master-system-v3-design.md

## Global Constraints

- Evidence before claims; process exit code alone is insufficient to mark a phase PASS.
- Fail closed on missing history, uncertain paths, source/report hash mismatches, absent reports, malformed metrics, or incomplete logs.
- One self-contained .cmd is the primary entry point; no separate persistent helper scripts are required for normal execution.
- Windows PowerShell 5.1 is the required compatibility floor; PowerShell 7 is optional.
- Never close, reconfigure, log into, or manipulate the ordinary MT5 terminal.
- The portable sandbox must not contain copied common.ini, account profiles, saved logins, chart profiles, or ordinary-terminal MQL5\Profiles state.
- Validation mode may read source/EX5 and stage verified EX5 copies; it must not rewrite MQL5 source or EX5 files.
- Do not retry an unexpected terminal exit until diagnostics classify it and identify an evidence-based remediation.
- GitHub Actions and CircleCI remain the canonical remote CI/research systems; do not duplicate those workflows.
- Do not print tokens, saved logins, refresh tokens, API keys, or full environment-variable dumps.
- No broker-account connection, broker API, cTrader Open API, production strategy activation, live order submission, or live-trading enablement is in scope.

## Review Focus

1. **Malformed or duplicated payload markers, BOM/CRLF, or quoted paths:** prove only the text between unique complete marker lines is extracted, and PowerShell 5.1 parses it without running MT5.
2. **Boolean string coercion and phase-state corruption:** tests must reject string values where a Boolean is required and reject invalid phase states/transitions.
3. **Missing, unreadable, or ambiguous tester logs and secrets in logs:** missing proof means UNKNOWN_BLOCKED; credential-like fields are redacted before persistence.
4. **Path aliases, accidental reuse of the ordinary terminal, or account artifacts in the sandbox:** canonical paths and sensitive-file inventories must block ambiguous or contaminated sandboxes.
5. **Locked, missing, or mismatched HCC/TKC files and month-range boundary errors:** exact hash and date/month coverage assertions must fail the cache gate.

---

## File and Interface Map

- Create **qa/windows/AUREON_MASTER_SYSTEM_V3.cmd** — sole normal entry point; CMD bootstrap and embedded PowerShell payload; diagnostic/self-test modes; phase orchestration.
- Create **tests/aureon-master-system-v3.test.ts** — cross-platform contract tests aligned with the existing Node test runner; Windows-only integration check for the launcher's non-destructive self-test.
- Modify **docs/superpowers/specs/2026-10-14-aureon-master-system-v3-design.md** only for status/approved decisions or evidence-backed clarifications; no functional product code in the spec.
- Generate runtime evidence only beneath a unique **qa/artifacts/master-system-development-<timestamp>/** run directory; do not commit generated terminal logs, reports, caches, account data or credentials.
- Leave **.github/workflows/ci.yml**, **.circleci/config.yml**, production React/TypeScript code, and all four EA source/EX5 files unchanged unless an independently reviewed defect requires a separate patch.

### PowerShell payload contracts

- New-RunContext([string] $EvidenceRoot) -> PSCustomObject with RunId, StartedAt, RunRoot, phase states and artifact paths.
- Set-PhaseState([string] $Name, [string] $State, [string] $Reason, [string] $ArtifactPath) -> void; State is restricted to NOT_RUN, RUNNING, PASS, BLOCKED, FAIL, SKIPPED.
- Write-EvidenceRecord([string] $Name, [object] $Value) -> string path; creates a unique evidence artifact and never overwrites an earlier run.
- Get-ToolchainInventory([string] $RepoRoot) -> PSCustomObject; every tool result is PASS, MISSING, UNAVAILABLE or BLOCKED, with versions only and no credential material.
- Collect-TesterDiagnostics([string] $SandboxRoot, [string] $Variant, [string] $Destination) -> PSCustomObject; gathers existing logs/config/hash/process/report-path evidence without launching MT5.
- Classify-TesterFailure([object] $Diagnostics) -> PSCustomObject with State, ReasonCode, EvidencePaths and RetryAllowed; unknown conditions return UNKNOWN_BLOCKED and RetryAllowed=false.
- Test-CompileEvidence([string] $ReportPath, [string[]] $VariantPaths) -> PSCustomObject with one result per expected variant and source/EX5 hash comparison.
- Get-RequiredTickMonths([datetime] $FromDate, [datetime] $ToDate) -> string[] using inclusive calendar months; current configured range must resolve to 202510 through 202610.
- Copy-VerifiedCacheFile([string] $Source, [string] $Destination, [string] $ExpectedSha256) -> PSCustomObject; a PASS requires independently computed source and target SHA-256 equality.
- Test-PortableSandbox([string] $SandboxRoot, [string[]] $OrdinaryTerminalRoots) -> PSCustomObject with canonical path checks and an account-artifact scan.
- New-TesterConfig([string] $Variant, [string] $SandboxRoot, [datetime] $FromDate, [datetime] $ToDate, [string] $ReportPath) -> string path to the exact INI used.
- Test-Mt5Report([string] $ReportPath, [object] $ExpectedConfig) -> PSCustomObject; absent/contradictory metrics remain null/unknown, never zero by default.

## Tasks

### Task 1: Establish regression contract tests before implementation

**Files**
- Create: tests/aureon-master-system-v3.test.ts
- Test: npm test

- [ ] **Step 1: Add failing launcher contract tests** for the exact unique marker pair, required self-test mode, required phase-state labels, explicit Boolean expressions at gate call sites, presence of the diagnostic-only mode, and absence of broker-login/order-start commands.
- [ ] **Step 2: Run the focused test** with node --experimental-strip-types --test tests/aureon-master-system-v3.test.ts. Expected: FAIL because the launcher has not yet been added.
- [ ] **Step 3: Add a marker-fixture test** that proves marker-like substrings in CMD bootstrap text are ignored, duplicate or missing whole-line markers fail, and only content strictly between the two exact marker lines is extracted.
- [ ] **Step 4: Run npm test** and record the expected red baseline in the task evidence; do not modify the existing product test harness.
- [ ] **Step 5: Commit** the failing regression tests as test: define AUREON master system V3 contracts.

### Task 2: Implement the one-file CMD bootstrap, PowerShell 5.1 self-test and evidence state model

**Files**
- Create: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- The launcher supports --self-test, --diagnose-existing <run-directory>, and normal orchestrated execution.
- New-RunContext, Set-PhaseState and Write-EvidenceRecord implement the payload contracts above.

- [ ] **Step 1: Implement the smallest embedded-payload extractor** using one unique begin-marker line and one unique end-marker line; marker matching is whole-line and case-sensitive, exactly one pair is required, and payload is written/executed as plain text rather than Base64-decoded.
- [ ] **Step 2: Add the failing self-test assertions** for marker count, PowerShell 5.1 parser success, unique run ID/evidence path creation in a temporary fixture, and the guarantee that self-test does not start terminal64.exe, copy caches, or alter EA files.
- [ ] **Step 3: Implement strict phase-state validation** with the exact six states; reject unknown state strings and string-to-Boolean coercion. Each phase transition is recorded with timestamp, reason and artifact path.
- [ ] **Step 4: Implement run-folder creation and failure handling** so a failed bootstrap records the error when possible and returns a non-zero process exit code; prior run evidence must never be overwritten.
- [ ] **Step 5: Run qa/windows/AUREON_MASTER_SYSTEM_V3.cmd --self-test** on Windows PowerShell 5.1 and require a machine-readable PASS result, no MT5 process launch, and no cache/source mutation.
- [ ] **Step 6: Run node --experimental-strip-types --test tests/aureon-master-system-v3.test.ts and npm test**. Expected: all contract and current-project tests pass.
- [ ] **Step 7: Commit** as feat: add AUREON V3 single-file bootstrap and self-test.

### Task 3: Diagnose the existing MT5 tester failure without launching MT5

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- Collect-TesterDiagnostics and Classify-TesterFailure follow the signatures above.
- Diagnostic-only execution reads a supplied existing run directory and never starts, stops or reconfigures a terminal or agent.

- [ ] **Step 1: Add tests** for missing logs, unreadable files, absent launch INI, missing staged EX5, report absent, contradictory exit/report evidence, a broker-authentication signature, redaction, and a log bundle with insufficient evidence. Insufficient evidence must classify UNKNOWN_BLOCKED; authenticated account evidence must classify SECURITY_BLOCKED.
- [ ] **Step 2: Run those tests** and confirm failure against the empty diagnostic implementation.
- [ ] **Step 3: Implement bounded diagnostic collection** for terminal YYYYMMDD logs, MQL5 logs, Tester logs, Tester/Agent-* logs, launch INI, staged EX5 path/hash, report search paths, process start/end/exit code, and a bounded Application Event Log query when available.
- [ ] **Step 4: Implement secret redaction** before copying excerpts or emitting JSON; preserve unmodified raw log files only inside the isolated QA evidence area when they contain no account or credential material. If raw files could contain secrets, preserve the original under access-controlled local evidence only and emit redacted copies to ordinary summaries.
- [ ] **Step 5: Implement the failure classifier**. For exit code -1000012353, do not infer a cause from the code alone. Use only a log signature or a proven missing precondition; otherwise report UNKNOWN_BLOCKED and disable automatic retry.
- [ ] **Step 6: Run --diagnose-existing against the existing master-system-development-20261014-125248 diagnostics for FVG_Scalper_V2_17_FORWARD_VALIDATION.** Expected: a diagnostic bundle with listed inputs, discovered files and a reason code; if the existing bundle is incomplete, state UNKNOWN_BLOCKED and identify the exact missing evidence. No MT5 process may start.
- [ ] **Step 7: Run focused tests and npm test**, inspect redaction and error-path artifacts, then commit as fix: collect isolated MT5 tester diagnostics safely.

### Task 4: Add toolchain inventory, repository status and compile-evidence validation

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- Get-ToolchainInventory and Test-CompileEvidence follow the signatures above.

- [ ] **Step 1: Add tests** for missing executables, version command failure, inaccessible repo, dirty working tree, absent or invalid compile report, non-zero warnings/errors, mismatched source/EX5 hashes, missing variant, extra/unexpected variant and secret-safe tool output.
- [ ] **Step 2: Run tests to confirm failure** before implementing the gates.
- [ ] **Step 3: Implement inventory** for PowerShell, Git, GitHub CLI, Node/npm, Python, .NET SDK, MetaEditor and terminal64.exe; classify each separately, do not install tools or authenticate automatically, and do not dump the environment.
- [ ] **Step 4: Implement repository evidence** for root, current branch, working tree, last commit and existing CI references. Never push, switch branch, modify shared refs, deploy or alter remote CI automatically.
- [ ] **Step 5: Validate the latest eligible successful compile-20261014-105645 evidence** against all four expected variants, report schema/status, source hashes, EX5 hashes, error/warning counts and required source invariants. Never rewrite MQL5/EX5 during validation.
- [ ] **Step 6: Run the focused tests and npm test**; require independent PASS/BLOCKED results per tool and EA variant.
- [ ] **Step 7: Commit** as feat: validate AUREON toolchain and native compile evidence.

### Task 5: Build and verify the isolated portable sandbox and account-safety gate

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- Test-PortableSandbox follows the signature above.
- The normal terminal is read-only for path discovery; no window/process stop, relogin or configuration mutation is permitted.

- [ ] **Step 1: Add tests** for exact-path collision, canonicalized aliases, sandbox nested in an ordinary terminal data root, incomplete portable-terminal copy, common.ini/profile/login artifacts, and inability to prove sandbox identity.
- [ ] **Step 2: Run tests to confirm failure** against the unimplemented sandbox gate.
- [ ] **Step 3: Implement canonical path discovery and the sandbox gate**; the isolated portable terminal must live in a distinct writable path, and reuse is allowed only after the required directory structure and terminal binaries are verified.
- [ ] **Step 4: Reject copied login/account/profile state** including common.ini, account/login stores, saved chart profiles and ordinary-terminal MQL5\Profiles content. Record only path and file category in evidence, not secret contents.
- [ ] **Step 5: Implement fail-closed broker-session checks** before and after a pilot: any authenticated account/session evidence yields SECURITY_BLOCKED; unreadable or ambiguous connection evidence yields UNKNOWN_BLOCKED. Both block subsequent tests.
- [ ] **Step 6: Run self-test and sandbox-only tests**. Expected: the real ordinary MT5 remains running and unmodified; any ambiguous/contaminated sandbox is blocked before launch.
- [ ] **Step 7: Commit** as feat: isolate native tester and enforce account safety.

### Task 6: Implement deterministic minute-history and real-tick cache synchronization

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- Get-RequiredTickMonths and Copy-VerifiedCacheFile follow the signatures above.

- [ ] **Step 1: Add tests** for exact required monthly list 202510–202610, inclusive end-month behavior, month/year boundaries, empty date range, missing HCC/TKC, target mismatch, locked source, unavailable VSS, and source/target SHA-256 mismatch.
- [ ] **Step 2: Run the focused cache tests** to confirm they fail before implementation.
- [ ] **Step 3: Implement the minute-history manifest** for XAUUSD history files, with canonical source/target paths, size, modification time, SHA-256 and verification method.
- [ ] **Step 4: Implement real-tick month enumeration and validation**; all 13 monthly TKC files must be present for 2025-10-14 through 2026-10-13 and each staged copy must have matching source/target hashes.
- [ ] **Step 5: For a locked history file, try VSS only if the required Windows component and permissions are available.** Record snapshot identity and content hash; if no consistent, verified copy exists, BLOCK the test. Never accept size/timestamp alone as file identity.
- [ ] **Step 6: Run cache tests against synthetic fixtures** and the current local cache without launching MT5. Require all required months and M1 history ranges to match.
- [ ] **Step 7: Commit** as feat: verify isolated XAUUSD history and tick caches.

### Task 7: Stage the verified EA, generate exact tester configuration and execute a single-variant pilot

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- New-TesterConfig and Test-PortableSandbox follow the signatures above.
- The preflight diagnostics/account gate must pass before any tester process launches.

- [ ] **Step 1: Add tests** for wrong Expert relative path, missing EX5, staged hash mismatch, altered test dates, wrong symbol/timeframe/model, optimization enabled, remote/cloud agents enabled, visual mode enabled and any non-zero live-trading flag.
- [ ] **Step 2: Confirm these tests fail** with the current implementation.
- [ ] **Step 3: Implement staging and INI generation** using exact isolated MQL5\Experts subfolder and relative Expert field; write every test parameter to the evidence record.
- [ ] **Step 4: Pin the pilot configuration** to FVG_Scalper_V2_17_FORWARD_VALIDATION, XAUUSD/M1, Model=4 real ticks, 2025-10-14 through 2026-10-13, USD 10,000 initial deposit, 1:100 leverage, EA default inputs, optimization off, local agents only, remote/cloud agents off, visual mode off and AllowLiveTrading=0.
- [ ] **Step 5: Verify launch contract against the installed terminal build** using the generated INI and logs; use only the intended copied portable terminal and never attach the EA to an ordinary chart. The command-line launch must use the isolated terminal plus its custom config; verify the actual path and config in logs before treating it as started.
- [ ] **Step 6: Launch only the single pilot after every preflight gate passes.** On any unexpected exit, collect diagnostics once and stop; no blind retry and no 4-EA batch.
- [ ] **Step 7: Re-run the account-session scan and collect process/log/report evidence** as soon as the pilot stops. A confirmed broker login/session blocks promotion to report validation and the next test.
- [ ] **Step 8: Run pilot configuration tests and npm test**, then commit as feat: run guarded single-variant native tester pilot.

### Task 8: Validate native HTML reports and produce final immutable evidence

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

**Interfaces**
- Test-Mt5Report follows the signature above.
- Report validation accepts only the expected EA/symbol/timeframe/date/model and a non-empty parseable native report.

- [ ] **Step 1: Add tests** for no report, zero-byte report, malformed HTML, mismatched variant or date, contradictory modeling status, absent metrics and locale-formatted numeric fields.
- [ ] **Step 2: Run the focused tests** and confirm failure before report parser implementation.
- [ ] **Step 3: Implement HTML existence/size/parse/config consistency checks** and hash the raw report without modifying it.
- [ ] **Step 4: Extract only actually present metrics**; unknown values remain null with an explanatory status, never fabricated zero or inferred performance.
- [ ] **Step 5: Emit master-system-summary.json, master-system-log.txt, per-variant manifest, tester INIs/log paths, cache manifest, source/EX5/report SHA-256 manifest, phase states and explicit unknowns.** Each run writes to a new timestamped path; evidence artifacts from earlier runs are not overwritten.
- [ ] **Step 6: Run report fixtures and the full local test suite**. Expected: synthetic valid report passes, each missing/contradictory fixture blocks as specified, and raw-report SHA-256 remains unchanged.
- [ ] **Step 7: Commit** as feat: validate tester reports and emit auditable evidence.

### Task 9: Gate the remaining three variants behind pilot success and complete end-to-end verification

**Files**
- Modify: qa/windows/AUREON_MASTER_SYSTEM_V3.cmd
- Modify: tests/aureon-master-system-v3.test.ts

- [ ] **Step 1: Add orchestration tests** proving variants 2–4 never launch when the pilot report or completion logs are missing, any account-safety gate is not PASS, or failure classification is UNKNOWN_BLOCKED/SECURITY_BLOCKED.
- [ ] **Step 2: Confirm the batch-gating tests fail** before wiring the state machine.
- [ ] **Step 3: Implement sequential execution** of the four expected variants only after a complete valid pilot report and matching tester completion logs. Reuse the valid V217 pilot result as the first variant for that same configuration; do not duplicate a full-year run unless the config differs.
- [ ] **Step 4: Re-run account, sandbox, cache, EX5 hash and configuration gates before each subsequent variant.** Stop immediately on any failure.
- [ ] **Step 5: Execute npm test, npm run build, Python research syntax checks and the launcher self-test.** Check existing GitHub Actions/CircleCI results through their connected service when available; if authentication/evidence is unavailable, record UNAVAILABLE rather than claiming PASS.
- [ ] **Step 6: Inspect the branch diff and generated evidence for accidental production changes, secret leakage, normal-terminal changes, missing hashes and unsupported claims.** All four EA source/EX5 inputs must remain unchanged.
- [ ] **Step 7: Commit** as test: verify AUREON V3 end-to-end gates and delivery evidence.

### Task 10: Final code review and handoff

- [ ] **Step 1: Review the full feature-branch diff** against every acceptance criterion in the approved design specification; fix any uncovered criterion with its own failing test first.
- [ ] **Step 2: Verify the branch contains no changes to main, production deployment configuration, account/login artifacts, source EA logic or live-execution pathways.**
- [ ] **Step 3: Produce a concise handoff** with exact launcher path, self-test command, diagnostics-only command, compile evidence status, pilot report status, four-variant status, hashes, CI evidence, and unresolved blockers.
- [ ] **Step 4: Keep the feature branch unmerged and deployment untouched** pending final owner review; a successful compile or backtest is not a profitability/live-readiness certification.

## External command-line reference

- Official MetaTrader 5 Start / Command Line reference: https://www.metatrader5.com/en/terminal/help/start_advanced/start. The installed terminal build and generated tester logs remain the acceptance authority for actual configuration parsing and test execution; documentation alone does not prove a test ran.
