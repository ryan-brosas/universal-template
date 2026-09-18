---
title: bend-coding-practices
summary: "Use during project stack selection or substantial architecture/domain-logic changes to assess Bend proactively, and when implementing .bend code, laws/proofs, JS/TS interop or native parallel computation. Covers adoption, reusable verified foundations and verification."
kind: playbook
---

# Bend Coding Practices

Bend 2 is an adopted option across our project stack, not a mandatory dependency
or replacement for existing languages. Use it for concrete product benefits.

## Project adoption

At initial stack selection or substantial architecture/domain-logic changes,
assess Bend even when not requested by name. Reuse an existing project decision
until requirements or constraints change; skip unrelated and trivial edits.

- Identify a real module, its invariants, caller and deployment target. Candidates
  include exact allocation, domain rules, state transitions and pure algorithms;
  independent, balanced CPU/GPU work is another opportunity.
- Choose adopt, defer or skip with a concrete reason in the existing project plan
  or architecture notes. Check dependencies, target support, maintenance cost and
  expected benefit. Missing evidence calls for a bounded integration probe, not
  automatic adoption. Do not create a separate decision registry.
- On adoption, implement an actual consumer-facing module with proofs and tests,
  not a disconnected demo. Keep useful UI, database and integration layers.
  Broader Bend ownership is possible when dependencies and deployment support it.
- Check the pinned revision's capabilities. Bend 2 differs from Bend 1/HVM; old
  syntax and performance claims do not carry over. The JS target is sequential:
  native parallelism does not automatically accelerate JS, network or LLM calls.

## Implementation workflow

1. Record and pin the compiler version/revision and backend in the consuming
   project. Use `bend guide`, `bend --help` and matching upstream source for
   syntax, libraries, loader/preload configuration and build requirements.
2. Inspect existing types, arithmetic, ordering lemmas and proofs before creating
   new foundations. Reuse suitable project/upstream definitions. Reproduce
   multi-argument or proof limitations against the pinned revision before calling
   them unsupported; create shared libraries only for real consumers.
3. Give each responsibility one implementation. Call Bend-owned logic from the
   host instead of duplicating it in JS/TS. Validate inputs and conversions at
   that boundary; exercise the real caller and selected deployment backend.
4. Formalize requirements in `LAWS.bend` and matching proofs in `PROOF.bend`.
   Review statements against product intent. Implementation edits must satisfy
   laws, not silently weaken them; requirement changes need explicit law review.
   Follow explicit types, affine ownership and termination requirements.
5. Keep proof-trusted definitions free of `@unsafe`; review necessary unsafe IO
   separately and state the trust boundary. Exit 0 with unsafe warnings does not
   establish logical soundness. Compiler/runtime correctness remains trusted.
6. Run `bend PROOF.bend` after relevant edits and require proof checks in project
   verification/CI. Check every intended proof entry point: an application check
   does not discover separate laws. Proof imports can check during loading, but
   verify the real loader/build retains them; keep explicit checks too.

## Verification

- Retain behavioral and integration tests. Proofs do not validate host callers,
  conversions, foreign effects, databases or external services.
- In an isolated fixture, break an implementation without changing its law;
  confirm rejection for that law. Remove a proof and confirm an unproven-goal
  failure. Syntax errors or missing tools are not passing negative tests.
  Restore mutations and rerun the positive path.
- Compare performance on the actual workload, including relevant compilation,
  startup and transfer costs. For correctness, assess meaningful invariant
  coverage and proof-maintenance effort. Toy proofs and upstream benchmarks
  alone do not justify production adoption.

## References

- [Official repository and current limitations](https://github.com/bendlang/bend)
- [Language, proofs, interop and tooling guide](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md)
