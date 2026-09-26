---
title: false-green-gates
summary: Use when a gate, suite, check, or tool command reports success without proving the capability ran - nonzero skip counts on passing runs, budgets enforced without evidence, a regression fixture failing inexplicably against supposedly-working code, a submitted value appearing in rendered output treated as a saved record, or an acknowledgement such as "done", "saved" or "scrolled" with no observable effect, and when a count was read under a filter or scope that was still applied. Triage skip causes, bisect dead paths with temporary probes, repair counter-gate collisions, and assert the effect on an observable only the effect can change rather than trusting the acknowledgement.
kind: playbook
---

# False-green gates and dead paths

## Purpose

Green is a claim about evidence, not exit codes. Observed failure class: a budget
suite "passes" with every test skipped, and a whole code path (file-backed
transcript refresh) ships silently dead because an early-return gate compared
two differently-scoped counters - reviewed, merged, and only exposed when a new
fixture encoding correct behavior failed inexplicably. A write read back as
applied because the submitted value appeared in the page dump belongs to the
same class: the read found the input field, not a new record.

## When to Use / NOT

- **Use when:** a passing run shows nonzero skip counts; an enforcement env
  produces green without capability evidence; a regression fixture fails while
  the code under test reads correct; a gate looks right but the trace dies inside it.
- **NOT when:** a test plainly fails with a readable cause
  (`../debugging-and-error-recovery/README.md`) or the question is which test to
  write (`../test-generation/README.md` owns catch-first mechanics).

## Approach

1. **Read the counts, not the exit code.** `0 pass / N skip / 0 fail` means the
   suite did not run. Record pass/skip/fail by name; skip-on-green is an open
   question, never closure.
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
3. **An inexplicably failing fixture means suspect the path is dead.** When a
   fixture encodes correct behavior and the code reads correct, the production
   path under test may never execute. Do not adjust the fixture to match
   observed behavior.
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
8. **A write read back as its own input is not verified.** After a submission, a
   match for the submitted value in the surrounding read can be the field still
   holding it, especially when the read is rendered text rather than the
   authority's record. Confirm the effect where the authority keeps it (response
   status, row or record count), then confirm identity with an independent query
   for the record. The same read explains why an unchanged count is not proof of
   failure: a duplicate can be rejected with no error surfaced. Search for the
   record before retrying, retry at most once, and report silence as unverified
   rather than applied.
9. **An acknowledgement is not an execution.** A command can report success
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

## Verification

Counts are named and each skip cause classified with evidence; probe sites are
removed from the diff; the repaired path has a fixture that failed before the
repair; new timers and watchers have their inverse (dispose/cancel) and are
rearmed per event; a write claim cites the authority's effect and an independent
identity query, not the submitted value.
