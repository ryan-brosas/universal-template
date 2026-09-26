---
title: false-green-gates
summary: Use when green checks, tool acknowledgements, saved-record claims, filtered counts or completion summaries lack matching evidence - skipped checks, omitted enforcing-lane phases, dead paths, echoed inputs and effects that never happened. Triage skips, bisect dead paths, verify effects through independent observables, and reconcile claims.
kind: playbook
---

# False-green gates and dead paths

## Purpose

Green is a claim about evidence, not exit codes. Observed failure class: a budget
suite "passes" with every test skipped, and a whole code path (file-backed
transcript refresh) ships silently dead because an early-return gate compared
two differently-scoped counters - reviewed, merged, and only exposed when a new
fixture encoding correct behavior failed inexplicably. A submitted value found
in a page dump can likewise be the unchanged input, not a saved record.

## When to Use / NOT

- **Use when:** a passing run shows nonzero skip counts; an enforcement env
  produces green without capability evidence; a regression fixture fails while
  the code under test reads correct; a gate looks right but the trace dies inside it;
  an ad-hoc probe reports a defect absent because its predicate tests a different
  mechanism than the consumer uses; a completion summary claims more than its
  verification results or saved evidence support.
- **NOT when:** a test plainly fails with a readable cause
  (`../debugging-and-error-recovery/README.md`) or the question is which test to
  write (`../test-generation/README.md` owns catch-first mechanics).

## Approach

1. **Read the counts, not the exit code.** `0 pass / N skip / 0 fail` means the
   suite did not run. Record pass/skip/fail by name; skip-on-green is an open
   question, never closure. Then check which status the harness actually propagated:
   a gate whose output is piped (`bun test | tail`, `pytest -q | grep`, `cmd | head`
   in a script, Makefile or CI step) reports the *last* command in the pipeline, so a
   failing suite exits 0. Observed 2026-09-18: `bun test … | tail -6` returned
   success while that same run printed `0 pass / 1 fail`. Use `set -o pipefail`
   (`bash -o pipefail -c`, or `${PIPESTATUS[0]}`), or stop piping the gate; a piped
   run is evidence only when the gate's own status reaches the caller.
2. **Triage the skip cause.** Distinguish environmental from structural before
   changing the install. Find the skip predicate (`describe.skip`, `hasX()`, an
   env flag) and evaluate it in the same runtime the suite uses. A missing
   module, file, or symlink is environmental: fix the lane. An export that loads
   while `hasX()` is false is structural — the class existing is not the
   capability (for example a test renderer compiled only for other OSes). Read
   the probe in the pin or binary you actually loaded (often a compile-time
   `cfg!` or OS/feature gate). Confirm with indexed source whether any branch
   enables this platform; if not, stop. Do not reinstall, rebuild, or open a
   native-feature change at this boundary. Under explicit enforcement, hard-fail
   on capable platforms and emit a loud named skip where the platform cannot
   provide the capability, recording the structural reason durably where the
   plan lives.
3. **Validate the fixture, then suspect a dead path.** First check the constructed
   input using [debugging's faithful reproduction step](../debugging-and-error-recovery/README.md).
   If the fixture encodes the intended contract and the code reads correct, the
   production path under test may never execute. Keep that fixture; do not adjust
   it merely to match observed behavior. For a local benchmark, check
   [host lifecycle parity](../performance-optimization/references/host-lifecycle-parity.md):
   passing helper tests may omit the runner's receiver state and deferred delivery.
4. **Bisect with temporary probes.** Add env-gated trace prints at candidate
   boundaries (function entry, after each await, immediately before the state
   patch), run the failing case once, read the trace to find the last live
   line, remove the probes. Expect misattribution - the trace picks the site,
   not the theory; one probe round per hypothesis. Use a monotonic clock for
   elapsed values in diagnostics; wall clock can jump.
5. **Check counter gates first.** `if (this.#counter !== counter) return` where
   the captured `counter` came from a *different* counter with a near-identical
   name (switch generation vs transcript-refresh generation) returns early
   unconditionally: dead code with no failure signal. Compare each counter only
   against its own entry capture.
6. **Repair and lock.** Fix the gate, keep the fixture that found it as the
   regression lock, and cite its failure against the unfixed code as the RED
   evidence.
7. **Give derived-state clears a re-read trigger.** Clearing derived state on an
   event (idle report, settle) while the authority (file, RPC) can lag leaves a
   content gap nothing re-reads: add a bounded one-shot catch-up rearmed per
   event, a watcher-driven recovery gated by file identity or mtime so foreign
   writes do not churn, and cancel it across ownership transitions.
8. **Compare the fast gate with the enforcing lane.** A subset command that omits
   phases the enforcement lane runs - a typecheck+unit "check" without the
   browser/probe/e2e stage - reports green without exercising those
   capabilities, and the omission surfaces later as a CI-only failure on a
   surface the subset never loaded. Enumerate the enforcing lane's steps, give
   the complete prepared-checkout sequence one executable command, and have that
   lane invoke the same command so the two cannot drift. The subset stays useful
   for iteration; it is not the evidence for a push.

9. **Do not read a write back as its own input.** Confirm the effect at the
   authority (response status or record count), then query the record
   independently to establish identity. An unchanged count can indicate a
   rejected duplicate rather than a lost write. Search before retrying, bound
   any retry, and report silence as unverified instead of applied.

10. **An acknowledgement is not an execution.** A command can report success
    while performing nothing, and a rejected command can look identical to a
    no-op when you only check for an exception. Prefer the response payload over
    the absence of an error: one tool answered a paging call with "Scrolled up"
    while the view never moved, and separate single-action calls were silently
    refused with an explicit disabled-code that read as normal when only the
    exception was inspected. Prove the effect on an observable that only the
    effect can change (a position, a count, a timestamp), and build the control
    from the same observable - a control page whose own dynamic content shifts
    will "prove" a no-op works. The same trap applies to scope: a count read
    while a filter is still applied is not the population, so clear or record
    the filter before trusting or reporting it.

## Boundaries

Probes are temporary instrumentation; remove them before merge and do not
convert probe output into permanent logging.

A pipeline is not a gate: it carries the exit status of its last command.

## Reconcile verification claims

Before handing back, compare the completion summary and any existing verification
record with actual tool results and saved files.

1. Keep each named check's outcome and available exit status when summarizing a
   batch; outer-wrapper success does not establish child-check success. Distinguish
   failed, skipped and unrun checks. Attribute counts to one named run; do not sum
   overlapping runs or combine a final aggregate with its earlier subsets.
   Group lifecycle events and transcript snapshots by execution ID (run plus
   tool-call ID where needed), pairing starts with terminal results. Repeated
   command text is not another execution; distinct IDs can be real retries of
   the same command. Without a terminal result, leave the outcome unknown.
2. For preservation claims, compare against a captured pre-edit content baseline.
   Name its repository/root, included/excluded paths and capture point, and keep
   the after-check and final claim within that scope. Include relevant untracked
   files and represent already-missing paths explicitly. One root's manifest says
   nothing about another root; status counts prove neither unchanged content nor
   authorship. Compare hashes only for matching path sets, label historical
   snapshots, and state the limit when a suitable baseline is missing. For exact
   edit claims, compare full contents or ordered diffs: line-set membership loses
   multiplicity and order, so duplicate insertions and rearrangements can vanish
   from its reported delta.
3. Read back files claimed to contain saved evidence. Tool output is not proof
   that a result was written to the claimed destination.
4. Confirm each check can fail before trusting a pass. A search or assertion whose
   "missing" outcome is still nonempty text - a `No matches found` line, an error
   document, an empty match object - satisfies a `length > 0` predicate while
   proving nothing. Run the check against a deliberately absent or broken input
   and require it to report failure there. Send positive and negative fixtures
   through the same collector, parser, predicate and result propagation used for
   the real claim. An unrelated file-existence probe does not validate a phrase
   or diff checker; printing a failure while returning success does not enforce
   a gate. Observed 2026-09-21: a phrase-presence check passed for every probe
   because its failure notice was itself nonempty.

Correct an existing record when authorized; otherwise report the mismatch. Do
not create a new report or rerun checks merely to reconstruct historical evidence.

## Verification

Counts are named and each skip cause classified with evidence; probe sites are
removed from the diff; the repaired path has a fixture that failed before the
repair; new timers and watchers have their inverse (dispose/cancel) and are
rearmed per event; the local gate and the enforcing lane share one aggregate
command, or every phase present in only one of them is named as a known gap.
A write claim cites the authority's effect and an independent identity query,
not the submitted value still sitting in a field. Command claims name the changed
observable, and counts record or clear any active filter.
