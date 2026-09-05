---
name: system-design-specification
description: "Use when a design has an explicit crash/recovery boundary to specify: write-ahead recovery, fault-site modeling, provisioned-ID intent, or deterministic crash testing; also durable asynchronous effects or event-sourced state whose failure behavior must be specified. Cold specialist, not generic system design."
invocation: manual
disable-model-invocation: true
---

# Crash-Recoverable Event System Specifications

Use this specialist for a design document with a real crash/recovery boundary.
For ordinary API, UI, service decomposition, or synchronous module design, use
project requirements and the relevant design owner instead. The existing skill
path remains available to explicit callers; it is not a generic hot entry.

## Start from the failure model

State the compatibility promises, non-goals, durability assumptions, effect
boundaries, and recovery outcomes that matter. Distinguish process death, timeout,
network ambiguity, storage failure, and concurrency: evidence for one does not
prove the others. Do not call a document or system "crash-proof" without a bounded
failure model and supporting evidence.

Choose the smallest specification technique that makes the relevant states and
recovery decisions inspectable. There is no required phase count, state-category
count, invariant quota, notation, identifier format, or error library.

## Select a focused reference

- **State ownership:** `references/state-ontology-and-invariants.md` illustrates
  an event-history/lane/log/settings split. Use it when those responsibilities
  exist; do not retrofit every system into four categories. Write the invariants
  needed to check this design, not an arbitrary number.
- **Ambiguous external completion:** `references/provisioned-id-protocols.md`
  explains durable intent and preallocated result IDs. Compare this with the
  project's transactions, outbox, remote idempotency, or reconciliation contract.
  An identifier alone does not deduplicate an external action.
- **Interleavings:** `references/trace-calculus-grammar.md` offers the E/R/L/G/H/X
  notation. Keep a project's sequence diagrams, state machines, or other notation
  when they expose the same ordering and persistence boundaries more clearly.
- **Recovery coverage:** `references/crash-site-matrices.md` maps modeled fault
  sites to durable observations and recovery actions. Record ambiguous outcomes
  explicitly; do not guess that a missing local result means no remote effect.

Use the project's error model: exceptions, discriminated results, or an effect
system as appropriate. Typed contracts can clarify recovery obligations without
requiring `Result<T, E>` everywhere. For repeatable tests, choose an existing
scheduler, fake clock, effect adapter, or fault injector; a manual drive API is
one option, not a required architecture.

## Verification

Trace each claimed recovery guarantee to an invariant, durable observation, and
applicable test/probe. Cover the modeled crash boundaries, duplicate delivery,
concurrent recovery, and replay authorization where relevant. Separate proposed
checks from executed evidence and report unsupported failure cases. Unsafe
external effects must not be replayed merely to make a recovery table complete.
