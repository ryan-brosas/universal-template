---
name: test-driven-development
description: Use when implementing a behavior change or fixing a reproducible defect - demonstrate the failure first (RED), fix, verify GREEN; for non-reproducible issues, use the strongest available failure evidence plus deterministic verification
disable-model-invocation: true
---


# Test-Driven Development

## Core Principle

**A claimed fix carries failure evidence.** For a reproducible defect or a behavior
change, the strongest evidence is a failing test first (RED), then the fix, then GREEN.
Write the test first when the behavior is testable; a test asserts observable behavior,
never implementation details. For a non-reproducible issue, use the strongest available
failure evidence (log, trace, probe, user report) and the strongest deterministic
verification afterward. Never fabricate a failing test to satisfy process.

## The Evidence Rule

<HARD-GATE>
**A fix ships with failure evidence and a passing verification.** Reproducible defect or behavior change: the test existed and failed before the fix (RED for the right reason), passes after (GREEN). Non-reproducible: the report names the strongest available failure evidence and the deterministic verification that was run. Skipping evidence is how a "fix" ships unproven.
</HARD-GATE>

## When to Use

Before feature implementation, bug fixes, or refactors that change testable behavior. REQUIRED BACKGROUND for `code-review-and-quality` and any feature work. Documentation-only changes and pure configuration need the project's normal verification, not a RED step.

## When NOT to Use

Documentation-only changes; pure configuration; throwaway prototypes explicitly marked as such.

## The Loop

```
RED:      write a failing test that captures the requirement
GREEN:    write the minimum code to make it pass
REFACTOR: improve the code while keeping tests green
```

Run the suite during implementation; don't defer all verification to the end.

## What a Test Is

A test asserts **observable behavior**: input → output, state change, side effect, or error contract. A test does **not** assert implementation details (private state, internal call order, mock interaction count) or that a specific function was called.

If your test breaks on refactor without behavior change, you wrote an implementation test. Rewrite as a behavior test.

## The RED Step

The test must fail for the **right reason**, the behavior is missing, not the test is broken. A test that doesn't compile is not RED. A test that passes on first run is not testing anything. Stop and rewrite.

## Common Rationalizations

| Rationalization | Counter |
|---------------------------|--------------------------------------------|
| "It's obvious" | If trivial, RED is trivial. Write it. |
| "Tests after" | There is no after. |
| "One-line change" | One-liners break builds. Test takes 30s. |
| "API stabilizes first" | Test IS the API design. |
| "Tested manually" | Not reproducible, not automatable. |
| "Mocking is faster" | Mocks test your assumptions, not behavior. |
| "Existing tests cover it" | Run them. Cite the output. |

## Workflow

1. **Read the requirement**, user-observable behavior + success criterion.
2. **Write failing test**, smallest capturing the behavior. Run. Confirm RED.
3. **Minimum code**, smallest change to pass. No "while I'm here" extras.
4. **Run**, confirm GREEN. If fails, debug, don't change the test.
5. **Refactor**, names, structure, duplication. No new behavior. Tests stay green.
6. **Verify**, full test file, not just the new test.


## Red Flags

Test passes on first run; test asserts implementation details; test breaks on refactor without behavior change; "I'll add tests later"; "obvious code" without test; "manual testing"; mocking the behavior claimed.

## Verification

- You saw RED for the right reason (behavior missing, not a broken test) before writing
 any production code.
- The minimum code made it GREEN with no "while I'm here" extras.
- The full test file, not just the new test, is green after the refactor.


## References

N/A, no reference files; the loop and rationalization table are fully specified in this file.

## Pi Fabric Boundaries

Tests are direct behavioral probes (black-box first). On pi hosts, transactional
mutation guards live in `skills/fabric-native-execution/` and project or `~/.pi/`
config; they are opt-in, never a prerequisite for ordinary test edits.
