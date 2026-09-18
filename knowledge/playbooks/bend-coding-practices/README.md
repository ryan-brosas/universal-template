---
title: bend-coding-practices
summary: "Use when adopting Bend 2, implementing or reviewing .bend code, writing laws and proofs, integrating with JS/TS, or choosing native CPU/GPU execution. Covers stack fit, proof boundaries and end-to-end verification."
kind: playbook
---

# Bend Coding Practices

Bend 2 is an adopted stack option for proof-checked application logic and suitable
native parallel computation, not a mandatory replacement for existing languages.
Use it for a concrete product benefit, not just to demonstrate that proofs work.

## Choose its role

- Consider Bend for important domain rules, state transitions and pure computation.
  It is not limited to numerical kernels; evaluate broader application ownership
  against the project's dependencies and deployment requirements.
- Keep established UI, service and integration layers where their ecosystem is
  needed. A Bend-owned core with JS/TS callers is a valid starting architecture.
- Check current upstream limitations before committing to a migration. Bend 2 is
  distinct from Bend 1/HVM; old examples and performance claims do not carry over.
- Native CPU/GPU parallelism suits independent, balanced work. The JS target runs
  sequentially. Do not promise faster network requests or LLM inference simply
  because orchestration or calling code moves to Bend.

## Implementation workflow

1. Record the compiler version or revision and selected backend. Use `bend guide`,
   `bend --help` and the matching upstream source for syntax, libraries and build
   requirements. Pin the toolchain in the consuming project for reproducibility.
2. Give each responsibility one implementation. If Bend owns a decision, have
   callers use that function rather than maintaining a second JS/TS version.
   Define input validation and data conversion at the host boundary.
3. Formalize meaningful requirements in `LAWS.bend`; implement matching proofs in
   `PROOF.bend`. Review the statements against product intent before trusting the
   result. Implementation changes must satisfy the laws, not silently weaken
   them. Requirement changes need explicit review of the changed statements.
4. Follow Bend's explicit types, affine ownership and termination requirements.
   Keep proof-trusted definitions free of `@unsafe`; review necessary unsafe IO
   loops separately and document what is outside the proof claim. An unsafe
   warning with exit 0 is not evidence of logical soundness.
5. Run `bend PROOF.bend` after relevant edits and make proof checking part of the
   project's required verification. Check every intended proof entry point:
   checking the application file alone does not discover a separate laws file.
6. For JS/TS interop, configure the documented Bend loader/preload and call exported
   pure functions. Importing `PROOF.bend` can also check proofs during loading;
   verify the actual consumer/build path retains that import. Keep the explicit
   proof check in verification rather than relying only on a side-effect import.

## Verification

- Run the proof check, then exercise the real caller and selected deployment
  backend. A proof about Bend code does not validate JS/TS callers, conversions,
  foreign effects, databases or external services.
- In an isolated fixture, break an implementation without changing its law and
  confirm rejection for that law. Remove a proof and confirm an unproven-goal
  failure. An unrelated syntax error or missing tool is not a passing negative
  test. Restore mutations and rerun the positive path.
- Retain integration and behavioral tests. Review unsafe definitions, assumptions
  and law changes; compiler/runtime correctness remains part of the trusted base.
- For performance adoption, compare the real workload against the existing
  implementation, including compilation, startup and transfer costs where
  relevant. For correctness adoption, assess meaningful coverage and proof
  maintenance effort. A toy proof or upstream benchmark is not adoption evidence.

## References

- [Official repository and current limitations](https://github.com/bendlang/bend)
- [Language, proofs, interop and tooling guide](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md)
