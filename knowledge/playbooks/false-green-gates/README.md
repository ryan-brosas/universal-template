---
title: false-green-gates
summary: Use when a gate, suite, or check reports green without proving the capability ran - nonzero skip counts on passing runs, budgets enforced without evidence, or a regression fixture failing inexplicably against supposedly-working code. Triage skip causes, bisect dead paths with temporary probes, and repair counter-gate collisions.
kind: playbook
---

# False-green gates and dead paths

## Purpose

Green is a claim about evidence, not exit codes. Observed failure class: a budget
suite "passes" with every test skipped, and a whole code path (file-backed
transcript refresh) ships silently dead because an early-return gate compared
two differently-scoped counters - reviewed, merged, and only exposed when a new
fixture encoding correct behavior failed inexplicably.

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
2. **Triage the skip cause.** Environmental (missing build profile, flag,
   checkout artifact) is fixed by changing the lane. Structural (a platform
   `cfg!`, an upstream limitation such as a test renderer gated to other OSes by
   the pinned runtime) is not fixable at this boundary: under explicit
   enforcement, hard-fail on capable platforms and emit a loud named skip where
   the platform cannot provide the capability, recording the structural reason
   durably where the plan lives.
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

## Boundaries

Probes are temporary instrumentation; remove them before merge and do not
convert probe output into permanent logging.

## Verification

Counts are named and each skip cause classified with evidence; probe sites are
removed from the diff; the repaired path has a fixture that failed before the
repair; new timers and watchers have their inverse (dispose/cancel) and are
rearmed per event.
