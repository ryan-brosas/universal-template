---
name: code-discipline
description: "Use when implementing, reviewing, or committing code, general code-discipline principles (scope, verification, type-safety, tests, context-gathering) farmed from high-quality repos."
invocation: internal
disable-model-invocation: true
---

# Code Discipline

## Core Principle

Gather context first, stay scoped to the problem, and earn conclusions from real failures, steer outcomes, not behavior.

## Workflow

1. Gather context: read the issue/PR, align on scope and shape, research relevant docs/APIs/patterns.
2. Make the narrowest change that resolves the reproduced behavior; stop.
3. Verify: attempt operations and quote real errors; work is done when CI is green and comments are resolved.
4. Commit: don't leave work uncommitted unless the user says otherwise.

General, language-agnostic code-discipline principles farmed from high-quality
open-source repos. These guide HOW to write code well, without over-restricting
behavior (steer outcomes, not behavior).

## Gather context first (trust but verify)

- Always start by gathering context about the task: read the issue/PR, ask the
 user about scope and shape, research relevant docs/APIs/patterns.
- Don't implement non-trivial code without alignment on the approach.

## Scope discipline

- **Be scoped to the problem.** For a bug fix, make the narrowest change that
 resolves the reproduced behavior, often one line plus one regression test,
 and stop.
- Don't widen a fix to sibling fields/providers/models on a hunch ("others might
 also be affected" is unacceptable). Only extend after confirming the shared
 defect by reproducing it.
- Don't refactor a shared abstraction to fix one caller unless the narrow fix is
 unavailable.

## Leave behavior unchanged for others

- A fix motivated by a narrow surface must not move observable behavior on a
 wider surface. Documenting it doesn't make it acceptable, only expected.

## Verification discipline

- **A restriction is a conclusion you earn from a real failure, not a field you
 read.** Never report an operation as blocked/unavailable based on a metadata
 flag or config field, attempt it and quote the actual error. If you
 can't attempt it, say "not attempted", never "we can't".
- **Pushing is not the end of the task.** Work is done when CI is green and there
 are no unresolved comments.
- **Do not leave work uncommitted.** Don't end a turn with unstaged or uncommitted
 changes unless the user says otherwise.

## Type-safety and quality

- Be fully type-safe (internally and in public API) without unnecessary `cast`s
 or `Any`s, so users don't need `isinstance` checks.
- Have comprehensive tests covering all code paths, favoring integration tests
 and real requests (recordings/snapshots) over unit tests and mocking.

## One source of truth

- Never store the same fact in two places; pick one source of truth.
- Extract inline business logic into reusable units (actions/services), never
 inline it in controllers, tools, or components.

## Design taste

- Prefer strong primitives, powerful abstractions, and general solutions over
 narrow, opinionated, or "battery-included" solutions.
- Be thoughtful and deliberate about new abstractions and public APIs, a wrong
 choice made in a rush is much harder to change later than to do right first.

## When to use

Apply these when implementing, reviewing, or committing code. For a **topic
index** (naming, docs, Git, AI, performance) load `coding-best-practices` first,
then return here for scope and verification. They complement
`agent-code-quality-gate` (the 5-check gate) and `quality-gate-methodology`
(how to write tests that catch).

## Red Flags

- Widening a fix to sibling fields/providers/models on a hunch ("others might also be affected") without reproducing the shared defect.
- Reporting an operation as blocked based on a metadata flag instead of attempting it and quoting the real error.
- Ending a turn with unstaged or uncommitted changes.
- The same fact stored in two places.
- Business logic inlined in controllers, tools, or components.


## References

- `coding-best-practices`, topic router (naming, docs, Git, AI, performance) when the question is broader than discipline alone.
