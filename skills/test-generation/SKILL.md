---
name: test-generation
description: "Use when writing, expanding, or auditing tests, converting exact recurring failures into gates, or deciding what to test. Catch-first method: prove a test can catch when reproducible, expand the right existing test, and avoid duplicate coverage."
invocation: entry
---

# Test generation: catch-first and evidence-based

## Core Principle

A test earns confidence by catching its intended failure class. When safe and
reproducible, prove that with a pre-fix failure and post-fix pass; otherwise use
the strongest direct evidence available.

## When to Use / NOT

- **Use when:** writing or expanding tests, auditing coverage or duplication,
  converting an exact recurring failure into a gate, or deciding what to test.
- **NOT when:** no meaningful failure mode can be stated, or the concern is
  semantic judgment or preferred agent behavior rather than an objective outcome.

## Workflow

1. **Name the gap first.** State the behavior, invariant, or failure class that
   matters and why existing evidence does not cover it.
2. **Test the class, not one incidental value.** Prefer a representative invariant
   or boundary unless specific values are themselves part of the contract.
3. **Test un-fixed AND fixed when reproducible.** The pre-fix run must fail and
   the post-fix run pass. If a safe pre-fix run is unavailable, record the
   strongest direct failure evidence instead of fabricating RED.
4. **Use the project's test inventory.** For a broad audit or multi-test change,
   keep a lightweight ledger of test names and targeted failure classes when it
   improves coverage decisions.
5. **Expand before duplicating.** When an existing test owns the escaped failure
   class, expand it. Add a new test when ownership or isolation is genuinely
   different.
6. **Promote recurring exact catches.** Convert a repeated, reproducible failure
   class into a maintained test or gate when its value exceeds false-positive and
   maintenance cost. Leave one-off or semantic judgment out of mechanical gates.
7. **Gate exact outcomes, not behavior.** Do not enforce that an agent researched
   or used a particular tool; test the objective artifact or runtime property.
8. **Keep test changes cohesive.** Group broad work into understandable cohorts
   when that improves review and diagnosis; do not split naturally cohesive code
   to satisfy a size ritual.
9. **Evolve on evidence.** Expand the suite when escaped defects reveal a
   valuable gap; do not create a standing test-growth ritual.

## Red Flags

- A new regression test is claimed to catch a reproducible defect without a RED
  run or equivalent direct failure evidence.
- Near-identical duplicate tests or orphan tests for variants owned elsewhere.
- A gate forces use of a tool or process instead of checking an objective result.

## Verification

- Every new or expanded regression test has a recorded pre-fix failure and
  post-fix pass when safely reproducible; otherwise the report names the direct
  failure evidence and limitation.
- When a ledger is warranted, it names each test and targeted failure class and
  exposes near-duplicate coverage.
- Repeated deterministic failure classes with positive maintenance value are
  covered by tests or gates; semantic judgment is not encoded as a behavior gate
  (`references/mechanical-gates.md`).


## References

- `references/test-ledger.md`, optional ledger structure and expand-before-duplicate
  evidence (scarywood75, 2026-08-03)
- `references/mechanical-gates.md`, qualification boundaries for deterministic
  tests, gates, and quality packs (scarywood75 + Tom, 2026-07-19)
- `references/cohort-discipline.md`, evidence on cohesive test cohorts and scratch
  tool promotion (Sewer56)
