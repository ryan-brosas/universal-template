---
name: agent-code-quality-gate
description: "Use when a coding agent claims implementation work is complete - an operational gate over scope, duplication, behavior tests, verification evidence, and regressions."
invocation: internal
disable-model-invocation: true
---

# Agent Code Quality Gate

Before claiming authored implementation or subagent work is done, inspect its
diff and the decisive verification output. Match depth to material risk; review
real boundaries rather than inventing reuse.

## Five checks

1. **Scope:** each authored change serves the request. Split unrelated cleanup
   without disturbing pre-existing user work.
2. **Duplication:** check likely shared boundaries for copied logic or competing
   owners. Consolidate only when reuse is real.
3. **Behavior:** use the closest decisive existing test or runtime probe. For a
   reproducible regression class, add or expand a durable test when its maintenance
   value is positive; otherwise state the remaining gap.
4. **Verification:** name the command/probe actually run and inspect its result,
   including any decisive output hidden by truncation. "Should work" is not proof.
5. **Regressions:** explain new failures, removed tests, and skips. Fix blockers;
   cosmetic nits do not block completion.

Explain legitimate exceptions in completion evidence or the commit: explicitly
approved scope, one-off duplication, quarantined flaky tests, or tests replaced
by better coverage. Do not hide exceptions or downgrade violated invariants.

Work is not done while an applicable blocking check fails; cosmetic nits are
reported without blocking. Report the inspected diff, commands, results, and
remaining limitations; do not repeat the checklist as a separate ritual or
substitute it for behavioral evidence.
