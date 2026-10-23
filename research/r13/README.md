# R13 native real-tick continuation

This folder holds lightweight cross-platform regression coverage for the R13 tester-worker startup policy. The Windows PowerShell controller, embedded EA and .set files remain in the separately delivered R13 source package; they are not silently represented as checked into this repository.

## Policy under test

- A missing visible worker during the first 89 seconds is treated as startup/warm-up, not an immediate fatal error.
- At or after 90 seconds, zero verified workers blocks the next case.
- An unverified worker is not accepted as the owned research worker.
- One path-verified worker remains accepted.
- More than one verified worker is an excess-agent failure.

This test is a pure model of the policy. It is not a substitute for the source-level checks and the native Windows/MT5 pilot documented in docs/R13_NATIVE_MT5_CONTINUATION.md.
