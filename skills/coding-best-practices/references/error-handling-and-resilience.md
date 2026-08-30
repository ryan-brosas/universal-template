# Error handling and resilience

## Core rule

**Errors are data at boundaries; happy path stays readable inside.** Validate and decode at the edge; trust narrow types internally (`typescript-coding-standards`, `security-and-hardening`).

## Prefer tests over catch-all handlers

- A broad `try/except` without a behavior test often hides bugs. Write a failing test first (`test-driven-development`), then handle the specific failure mode you proved.
- `quality-gate-methodology`: test un-fixed (fail) and fixed (pass) — the test must catch.

## Boundaries to handle explicitly

- User input, file I/O, network, subprocess, database, auth — each gets validation or typed error mapping at the boundary.
- Do not swallow exceptions without logging and a typed outcome; "log and continue" needs a documented invariant.

## Resilience patterns

- **Retry with backoff** only for transient, idempotent operations — cap attempts, jitter, and log final failure.
- **Fail fast** on programmer errors (assertions/invariants) vs **recover** on operational errors (network blip).
- **Graceful degradation** only when the product spec allows partial results — otherwise propagate.

## Anti-patterns (`testing-anti-patterns`)

- Testing mock call counts instead of observable outcomes.
- Test-only methods on production types.
- Empty catch blocks.

## Mechanical gates

- Behavior/regression tests in project CI
- Type checker (`mypy`, `tsc --strict`) where applicable
- Linter rules for bare `except` / swallowed errors where configurable

## Leaf skills

- `quality-gate-methodology`, `test-driven-development`, `testing-anti-patterns`
- Typed errors: `typescript-coding-standards`
- Security-related failures: `security-and-hardening`
