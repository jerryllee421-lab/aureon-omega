# AUREON V50 R13 — Native MT5 continuation gate

## Current state

- Supplied run evidence reports 28 of 48 continuous-period cases completed and validated.
- The next case stopped at RESOURCE_GUARD_NO_VISIBLE_WORKERS roughly three seconds after launch.
- The contemporaneous resource sample showed zero path-verified and zero unverified tester workers, while the MT5 parent remained alive and the native tester journal had just started a test.
- This is consistent with delayed worker visibility; the evidence does not prove the tester worker was absent or identify the exact Windows enumeration cause.
- The repaired external package reports a 90-second bounded startup warm-up and retains executable-path ownership checks and a no-process-termination invariant.
- The package's Python regression suite passed 5/5 in the available Linux environment. Native Windows PowerShell and MT5 execution has not been performed here.

## Safe continuation sequence

1. Run the repaired launcher on the target Windows machine with the isolated MT5_RESEARCH terminal only.
2. Execute one native Model=4 pilot. Do not start the remaining 20 cases until the pilot is reviewed.
3. Confirm the journal shows the expected symbol, period, EA/inputs and native real-tick model.
4. Confirm the ownership log records the expected terminal root and executable path; startup invisibility must remain non-fatal only inside the bounded warm-up.
5. Confirm the memory guard, disk guard, worker-count guard and no-process-termination invariant remain intact.
6. Validate each checkpointed case using its case hash, dates, strategy arm, native journal, report and completion status. Reuse only fully validated cases.
7. Resume only missing or invalid cases. Never convert missing results to zero, substitute OHLC/generated ticks, or overwrite the frozen V2.12 benchmark.
8. Keep all results research-only and DEMO-only. No live deployment approval follows from this controller repair.

## Release gate

Do not resume the full queue until the isolated native pilot passes. Stop safely if ownership remains unresolved after warm-up, a second worker appears, the terminal root is unexpected, the resource reserve is breached, or the native report/journal is incomplete.

## Boundaries

The Linux regression test validates a small pure policy model only. It does not prove PowerShell correctness, MT5 compilation, native tester execution, real-tick coverage, or strategy profitability. Those require the target Windows/MT5 environment and inspectable native evidence.
