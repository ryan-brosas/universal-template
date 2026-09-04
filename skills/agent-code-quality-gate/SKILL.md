---
name: agent-code-quality-gate
description: "Use when a coding agent claims implementation work is complete - an operational gate over scope, duplication, behavior tests, verification evidence, and regressions."
invocation: internal
disable-model-invocation: true
---


# Agent Code Quality Gate

## Core Principle

Completion claims require diff review and real verification evidence. Match test depth and duplication review to the change's material risk.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **Code-changed-this-session → review required.** Not optional.
- **Scope = authored diff scope.** Preserve unrelated user changes; do not add
  unrelated cleanup.
- **Behavior evidence = required.** Use a relevant existing test, a new regression
  test, or the strongest practical runtime probe.
- **Duplication review is proportional.** Inspect likely shared boundaries; do not
  extract hypothetical reuse.
- **Verification evidence = required.** Run the check, inspect the result, and
  report the decisive evidence.
</EXTREMELY-IMPORTANT>

## When to Use

Before declaring "done" after bugfix, feature edit, refactor, or subagent work. The agent's work passes through this gate before the user reviews.

## The Gate (5 Checks)

1. **Scope.** Does each authored line match the stated problem? Split or revert
   unrelated cleanup without disturbing pre-existing user work.
2. **Duplication.** Did the change copy established logic or create a competing
   owner? Consolidate only when reuse is real.
3. **Behavior evidence.** For a reproducible regression class, add or expand a
   durable test when its maintenance value is positive. Otherwise run the closest
   existing test or runtime probe and state the remaining gap.
4. **Verification evidence.** Named check ran and its decisive result was
   inspected. Not "should work".
5. **Regressions.** No unexplained new failures, removed tests, or skipped tests.

## Workflow

1. **Get the diff.** `git diff` (or staged, or branch vs main).
2. **Scope check.** Is every authored line traceable to the stated problem?
3. **Duplication check.** Inspect likely shared boundaries. Flag real repetition.
4. **Behavior check.** Run the closest decisive test or probe; add a durable
   regression test when the failure class earns one.
5. **Verification check.** Name the command or probe and capture its result.
6. **Regression check.** Explain any new failure, removal, or skip.
7. **Pass / fail.** If any applicable check fails, work is not done.

## Common Findings

| Finding | Action |
|----------------------------|--------------------------|
| "While I'm here" cleanup | Split or revert |
| Copy-pasted established logic | Reuse or improve its canonical owner |
| New test that doesn't test | Rewrite or delete |
| Skipped test (`.skip`) | Un-skip or fix |
| Removed test | Add back, or justify |
| No behavior evidence | Run the closest decisive test or probe |
| Truncation hides the result | Show the decisive range |

## Severity Tells

| Tell | Action |
|----------------|-------------------------------|
| `[blocker]` | Must fix. Violated invariant. |
| `[should-fix]` | Worth fixing now. Real cost. |
| `[nit]` | Cosmetic. Note, don't block. |
| `[question]` | Need clarification. |

## When to Override

| Override | When |
|------------------------------|-----------------------------------------|
| "Scope creep is acceptable" | User explicitly approved the extra work |
| "Duplication is acceptable" | One-time use, extraction premature |
| "Skipped test is acceptable" | Flaky, in test-quarantine |
| "Removed test is acceptable" | Replaced by a better test |

Document the override in the completion evidence or commit when one is made.
Don't hide it.

## Common Mistakes

Skipping the gate; "I checked, it's fine" without evidence; scope creep
unmarked; tests that do not catch; unexplained skips or removals; blockers
downgraded to nits.

## Verification

Run the 5 checks against the diff: scope, proportional duplication review,
behavior evidence, named verification evidence, and regressions. Any applicable
failed check means the work is not done.


## References

N/A, no reference files; this skill is self-contained.
