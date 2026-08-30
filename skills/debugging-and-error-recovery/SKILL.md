---
name: debugging-and-error-recovery
description: "Use when tests fail, builds break, behavior is unexpected, or multiple fix attempts have not worked."
---

# Debugging & Error Recovery

## Core Principle

Reproduce, localize, reduce, fix, and guard before claiming resolution. Random fixes create new bugs; move from symptom to root cause to guarded fix.

## When to Use

Test, lint, typecheck, build, or runtime failure; user-reported bug or unexpected behavior; a previous fix failed; error crosses multiple layers.

## When NOT to Use

Feature work with no failure signal (source-first implementation); pure research (`source-driven-development`).

## Workflow

1. Read the full error and relevant logs.
2. Reproduce the failure or state why it cannot be reproduced.
3. Localize the failing layer: input, boundary, business logic, integration, environment.
4. Reduce to the smallest failing case.
5. Form one hypothesis; test it with one change or one diagnostic.
6. Write a failing regression test when behavior can be tested.
7. Fix the root cause, not just the symptom.
8. Re-run the original reproduction and relevant regression checks.

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

N/A, no reference files; this skill is self-contained.
