---
name: typescript-coding-standards
description: "Use when choosing TypeScript domain models, validation boundaries, failure semantics, adapters, or test seams. Follow the project's architecture; brands, Result/Effect, and pure-core designs are options, not universal standards."
invocation: manual
disable-model-invocation: true
---

# TypeScript Domain Modeling Choices

Keep the existing caller path, but choose patterns from the domain's risks and
the project's conventions. For style, imports, or compiler/linter configuration,
use `../typescript-coding-practices/SKILL.md`. A simple script or module without
a meaningful domain boundary does not need a new architecture.

## Inspect before introducing a pattern

Read representative code, public types, runtime validation, error handling,
dependencies, and tests. Preserve working conventions unless changing them solves
a demonstrated problem. Do not add an effect library, schema generator, adapter
layer, or branding scheme merely because this skill mentions one.

## Decisions

- **Domain values:** use branded primitives when confusing compatible identifiers
  is a real risk. Plain strings/numbers can be enough for local values. A cast
  does not validate input; construct branded values at a trusted or validated
  boundary. Use discriminated unions when they rule out meaningful invalid
  states. Follow the existing discriminator (`kind`, `type`, `_tag`, or another);
  `type` is a valid property name.
- **Trust boundaries:** treat external input as untrusted and check what the
  operation requires. Use an existing schema decoder, parser, or explicit guard.
  Type assertions and TypeScript types alone provide no runtime validation.
  Prefer `unknown` plus narrowing over allowing unchecked values to spread;
  isolate a necessary `any` in a compatibility boundary and explain the limit
  rather than replacing it with an equally unsafe assertion.
- **Failure semantics:** use discriminated results or typed errors when callers
  need exhaustive recovery. Keep exceptions or rejected promises when they fit
  the framework and project contract. An established Effect/Result codebase
  should retain its model; an exception-based codebase need not migrate to it.
  Translate external failures at the boundary that owns that responsibility.
- **Effects and tests:** separate deterministic calculations from I/O where it
  makes testing or reasoning easier. Inject time, randomness, or clients when
  repeatability matters; direct calls can be appropriate in small orchestration
  code. Use adapters for meaningful isolation, not one interface per dependency.
  Choose real integration tests, fakes, or mocks for the behavior under test.
- **Modules:** expose the smallest useful public surface and keep ownership clear.
  Investigate cycles that cause initialization or coupling problems. Follow
  existing export and packaging conventions rather than banning all barrel files.

## Verification

Run the project's typecheck, lint, and relevant behavior tests. Exercise invalid
external input, caller recovery, and effect boundaries where changed. Verify that
brands are not mistaken for validation and mocks are not merely testing themselves.
Do not classify `try/catch`, `throw`, `Date.now()`, `any`, or an unbranded string as
a defect without its context and an actual failure risk.
