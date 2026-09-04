---
name: code-discipline
description: "Use when implementing, reviewing, or committing code, general code-discipline principles (scope, verification, type-safety, tests, context-gathering) farmed from high-quality repos."
invocation: internal
disable-model-invocation: true
---

# Code Discipline

## Core Principle

Gather enough context, stay scoped to the problem, and earn conclusions from
real evidence. Steer outcomes, not behavior.

## Workflow

1. Gather enough context to own the change; research material uncertainty.
2. Make the narrowest change that resolves the reproduced behavior.
3. Verify with decisive checks; attempt safe, permitted operations instead of
   inferring failure.
4. Commit or ship only when the request includes that delivery step.

General, language-agnostic code-discipline principles farmed from high-quality
open-source repos. These guide HOW to write code well, without over-restricting
behavior (steer outcomes, not behavior).

## Gather context first (trust but verify)

- Start from the request and relevant source. Ask about scope or research
  docs/APIs/patterns when uncertainty materially affects the implementation.

## Scope discipline

- **Be scoped to the problem.** For a bug fix, make the narrowest change that
  resolves the reproduced behavior, then stop.
- Don't widen a fix to sibling fields/providers/models on a hunch ("others might
 also be affected" is unacceptable). Only extend after confirming the shared
 defect by reproducing it.
- Change a shared abstraction only when the shared defect is confirmed and that
  abstraction owns the behavior.

## Leave behavior unchanged for others

- A narrow fix should not move unrelated observable behavior. When the owning
  shared boundary must change, verify and communicate the wider impact.

## Verification discipline

- **A restriction is a conclusion earned from evidence, not a field read in
  isolation.** When safe and permitted, attempt the operation and quote the
  error. Otherwise say "not attempted" and name the constraint.
- When delivery includes a pull request, inspect required CI and unresolved
  review comments before calling that delivery complete.

## Type-safety and quality

- Preserve the project's type-safety contract. Avoid unnecessary casts, broad
  escape types, and caller-side narrowing when a precise boundary is practical.
- Cover material behavior with the smallest useful mix of tests. Favor
  integration or real-request evidence when that boundary is the risk.

## One source of truth

- Never store the same fact in two places; pick one source of truth.
- Extract shared business logic when duplication or an ownership boundary earns
  a reusable unit; do not abstract a one-off solely for uniformity.

## Design taste

- Match abstraction breadth to established requirements and reuse; prefer the
  simplest primitive that keeps the design coherent.
- Review new abstractions and public APIs carefully because compatibility can
  make rushed choices expensive to change.

## When to use

Apply these when implementing, reviewing, or committing code. For a **topic
index** (naming, docs, Git, AI, performance) load `coding-best-practices` first,
then return here for scope and verification. They complement
`agent-code-quality-gate` (completion review) and `test-generation` (how to
write tests and exact gates that catch).

## Red Flags

- Widening a fix to sibling fields, providers, or models without evidence of a
  shared defect.
- Reporting an operation as blocked from metadata alone when a safe direct
  probe is available.
- Committing or shipping without a delivery request.
- Competing sources of truth for the same fact.
- Repeated business logic with no clear canonical owner.


## References

- `coding-best-practices`, topic router (naming, docs, Git, AI, performance) when the question is broader than discipline alone.
