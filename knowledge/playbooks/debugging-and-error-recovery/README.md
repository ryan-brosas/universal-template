---
title: debugging-and-error-recovery
summary: Use when tests fail, builds break, behavior is unexpected, or multiple fix attempts have not worked.
kind: playbook
---

# Debugging & Error Recovery

## Core Principle

Reproduce, localize, reduce, fix, and guard before claiming resolution. Random fixes create new bugs; move from symptom to root cause to guarded fix.

## When to Use

Test, lint, typecheck, build, or runtime failure; user-reported bug or unexpected behavior; a previous fix failed; error crosses multiple layers.

## When NOT to Use

Feature work with no failure signal (source-first implementation); pure research (`source-driven-development`); a passing suite whose only signal is skips (`../false-green-gates/README.md`).

## Workflow

1. Read the full error and relevant logs. For structured session logs, inspect one
   record's shape, parse it, then select by event type, role, tool name and
   correlation ID before searching content. Raw keyword searches also match
   diagnostic prompts, tool arguments and quoted history; their counts are not
   event counts. If a search returns the investigation itself, change selection
   strategy instead of tuning more regexes. Extract a bounded set of actual
   events and join related results by identity. Missing trigger or path metadata
   stays unknown; a changed path alone does not identify its writer. Use text
   search within the selected records when the payload is unstructured.
2. Reproduce the failure or state why it cannot be reproduced. To test whether a
   patch introduced it, run the same focused check at an unchanged revision in
   isolation with comparable dependencies and environment. Matching failures
   establish that the symptom predates the patch, not its root cause; differing
   failures or environments leave attribution open.
3. Localize the failing layer: input, boundary, business logic, integration, environment.
4. Reduce to the smallest failing case without silently repairing the input.
   For a failing test, inspect its fixture builders, defaults, setup and overrides
   alongside the fields the failing consumer reads. Test names and declared
   context do not establish the constructed object's metadata. First reproduce
   with that exact object and call path; a hand-built probe with changed defaults
   is a different case, even if it passes. Preserve the failing baseline, then
   vary one relevant input or boundary at a time. If the fixture contradicts its
   intended valid scenario, correct it without weakening the production guard;
   keep intentional malformed or foreign-input cases as negative regressions.
   Once inputs agree, continue tracing the failing layer.
5. Form one hypothesis; test it with one change or one diagnostic. Choose a probe
   that distinguishes competing explanations. Compare the authoritative record
   with the live projection: persisted output that is clean while an in-memory
   view of the same stream doubles or corrupts it narrows the investigation to
   differences between the paths; persistence may also deduplicate events.
   Check subscription cardinality at reuse boundaries — a
   pooled object re-attached without detaching its prior listener applies every
   event once per registration, even when an identity guard passes.
   A status label is not its implementation:
   trace its producer when it contradicts behavior. HTTP 5xx alone does not establish
   rate limiting; inspect the response and rate-limit headers for the failing request.
   Keep observations, hypotheses, and confirmed causes separate in reports and runbooks.
   Successful reads prove availability, not freshness or successful background sync.
6. Write a failing regression test when behavior can be tested.
7. Fix the root cause, not just the symptom.
8. Re-run the original reproduction and relevant regression checks.

For state that a partial failure can strand - a borrowed model, lock, handle or
lease - record the recovery information when the forward transition succeeds,
before later work can fail. If the compensating action also fails, keep that
record and name the owner that will retry it; clear it only after restoration
succeeds. Reproduce the double failure deliberately instead of assuming rollback
is the reliable path. When restarting loses that state, first check whether
[existing durable history can recover the obligation](references/journal-recovery.md)
before introducing another persistence mechanism.

## Retry Policy

A repeated failure under the same hypothesis is evidence against the hypothesis, not a reason to repeat it. When a fix does not change the failure: stop, invalidate the current hypothesis, and reopen the evidence and assumptions (re-read the request, the full error, and the touched code; check for a mapping problem before another attempt). Change approach or escalate when no new hypothesis is available, not at a fixed attempt count. Most repeated failures are a mapping problem, not an execution problem.

## Evidence Log

For complex bugs, keep a short log: Symptoms / Reproduction / Hypotheses Eliminated / Root Cause / Fix and Guard.

## Common Rationalizations

| Rationalization | Rebuttal |
|-----------------------------|-----------------------------------------|
| "Probably the issue" | Probably is a hypothesis, not evidence. |
| "Patch the symptom now" | Symptom patches hide root causes. |
| "Multiple fixes save time" | You won't know which change mattered. |
| "Test failure is unrelated" | Prove it with isolation first. |
| "One more attempt" | Same hypothesis + same failure = new hypothesis first. |

## Red Flags

Code changes before reproduction; fix before reading the full error; same failure persists across identical hypotheses; new failures in different layers; regression test skipped for a reproducible bug; success claimed without re-running the original failing scenario.

## Verification

Original failure reproduced or documented as non-reproducible; root cause stated with evidence; regression test or guard exists when feasible; original scenario and related checks pass.


## References

- `references/ui-state-ownership.md`, when a filter, tab, selection, sort, or draft
  changes after an action that should not edit it.
- `../local-service-durability/README.md`, when the failure is a supervised local
  service that crashes, restarts, or will not start.
