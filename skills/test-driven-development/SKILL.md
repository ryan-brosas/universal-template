---
name: test-driven-development
description: Use when implementing a behavior change or fixing a reproducible defect - demonstrate the failure first (RED), fix, verify GREEN; for non-reproducible issues, use the strongest available failure evidence plus deterministic verification
invocation: internal
disable-model-invocation: true
---

# Test-driven development

Use the red/green loop when a failing test will make the behavior change easier
to implement and verify. Prefer extending an existing test over constructing a
new harness.

1. Capture the observable requirement and run the smallest relevant test. Confirm
   it fails for the intended reason, not broken setup or a syntax error.
2. Implement the change and confirm the test passes.
3. Refactor if useful, then run nearby tests that cover the affected integration.

A test passing on its first run is not worthless: it may lock existing behavior.
For a claimed regression catch, use a safe pre-fix version or targeted mutation
when practical. Existing failing tests can supply RED without another test.
Manual probes, traces and production reports can provide failure evidence when
reproduction is unsafe or unavailable; state their limits and verify what can
be verified rather than fabricating RED.

Assert behavior at the owning boundary. Call order, timing and side effects are
valid assertions when they are the contract, not incidental implementation.
Mocks can isolate an external boundary but cannot prove that integration works.
Documentation, configuration and prototypes need checks suited to their risks,
not a test-first ritual.

See `../test-generation/SKILL.md` for broader coverage and gate decisions. No
transactional host mode or template infrastructure is required for test edits.
