# Repeat live dogfood without moving the goalposts

Use when repeating live agent or service tasks to test reliability and retain
comparable evidence. Repetition measures this workload's repeatability, not
production readiness. For superiority claims, use a
[matched control](controlled-dogfood-benchmarks.md).

## Freeze the batch before launch

Record the workload, acceptance criteria, runner/verifier revisions, loaded
runtime identity, configuration, requested sample count, and per-run turn, time
and spend limits. Distinguish a recorded-spend guard from a hard billing cap;
[shared budget accounting](shared-budget-accounting.md) covers what an
enforceable limit requires.
Capture scoped content baselines, including relevant untracked files and allowed
bookkeeping, as described in [verification reconciliation](../../false-green-gates/README.md#reconcile-verification-claims).
A retired observation scope needs a fresh baseline, not a clean verdict.

Smoke-test the actual runner and its summary parser on one saved receipt before
launching more paid work. Use [host lifecycle parity](host-lifecycle-parity.md)
when the runner supplies a partial host. A diagnostic request does not authorize
runtime repairs or relaxed acceptance criteria.

## Resume from receipts, not assumptions

Give each sample a fresh workspace and execution/session identity. Record its
launch and terminal receipt; after a handoff or timeout, inspect those before
launching again. A broken table printer is not a failed live run. Reprocess the
completed sample rather than paying to replay it. Keep all attempted samples,
including incomplete ones; apply the declared retry policy rather than silently
replacing failures.

A running process is not progress. Distinguish a live worker, a responsive
service, an advancing attempt and a terminal result, and name the latest
meaningful progress event with a bounded stall policy. A durable worker and its
foreground watcher have different lifetimes; stopping the watcher does not stop
the work ([service durability](../../local-service-durability/README.md)).

## Isolate the observer and the phase

For mutation-triggered behavior, keep diagnostic writes outside the watched scope
or buffer them until the probe ends. If bookkeeping is the intended input, retain
that case and label it; distinguish the original write from its later detection
boundary. A separate clean probe can isolate read-only behavior. Do not disable
the mechanism under test merely to keep the observer quiet.

Before resuming a process that appends to the same log, freeze the earlier phase's
bytes or record a verifiable event cutoff. Reading the shared file's final state
after recovery does not establish its state at the crash. A hash without the
corresponding bytes cannot reconstruct that state. Use phase-local receipts or
a verified prefix; if neither exists, leave the earlier state unobserved rather
than inferring it from a successful recovery.

## Keep verdicts separate

- **Task:** does independent verification pass on the produced artifact?
- **Lifecycle:** did execution reach the intended terminal state within limits?
- **Scope:** were writes and mutation attempts within the current authorization?
- **Coverage:** did the capability actually execute, or was it skipped, absent,
  failed, or unobserved?

An artifact can pass while the lifecycle hits a turn limit. A green verifier can
coexist with “nothing to compact”; that does not prove successful compaction.
Attribute a cap failure to the enforcing layer and event. A raised cap completing
later samples demonstrates observed headroom, not a universally sufficient limit
or proof that the product has no defect. Version a changed protocol separately
and retain the original failures.

## Diagnose the diagnostic before changing expectations

Read raw event types, identities, terminal results and relevant request payloads,
not substring counts. Separate deliberately failing baseline tests from unexpected
tool errors. Record who injected a follow-up: a probe-supplied steer after return
proves neither autonomous continuation nor mid-execution scope-change handling.
Label elapsed phases by their actual endpoints.

If a batch flag contradicts receipts, inspect the collector's data shape before
blaming the product: a numeric count is not an array. Preserve the first diagnostic
result and correct derived reports separately; do not rewrite sealed evidence.

Check the intended behavior, not incidental output shape. A harmless comment can
change line counts or hashes without changing assertions. Conversely, equal
assertion counts do not prove negative fixtures or assertion meanings survived;
inspect the actual diff and independently rerun verification. Distinguish a
parser correction from a changed requirement. The latter needs authorization and
a new protocol, not a post-hoc predicate that makes the batch green.

## Report only what the batch establishes

Retain per-sample outcomes, identities, commands, units, usage, cost provenance,
phase timings and unresolved observations. Label host cost estimates as estimates;
expose cache variance and missing provider-internal activity. Report medians and
spread with the included sample set, not a success-only denominator disguised as
all attempts. Verify archive hashes and preservation claims before declaring the
record complete. Name the next untested boundary instead of treating another
identical passing batch as broader coverage.
