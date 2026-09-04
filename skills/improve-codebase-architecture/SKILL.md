---
name: improve-codebase-architecture
description: Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
invocation: entry
---

# Improve codebase architecture

## Core principle

Start from a concrete maintenance, coupling, reliability, performance, or
navigation problem. Change the smallest coherent ownership boundary that
addresses its cause, preserve intended behavior, and verify the improvement with
the evidence the problem supports.

## When to use / NOT

- **Use when:** responsibilities are fragmented, changes require shotgun edits,
  interfaces are hard to test, dependencies point the wrong way, or build and
  navigation costs are materially slowing work.
- **NOT when:** there is no concrete problem, a local implementation fix owns the
  issue, or the request is a feature rather than an architecture change.

## Workflow

1. **Name the pain and affected behavior.** Identify callers, dependencies, and
   the boundary that currently owns the responsibility.
2. **Establish useful evidence.** Use tests, change patterns, dependency traces,
   runtime behavior, or a relevant metric. Do not require a metric when direct
   behavioral evidence is stronger.
3. **Choose the smallest coherent move.** Rename, extract, consolidate, move, or
   reshape an interface according to the actual cause. Avoid splitting a
   naturally cohesive module merely to reduce size.
4. **Protect behavior and integration.** Use existing tests and focused probes;
   add a regression test when the recurring failure class earns one.
5. **Implement in reviewable increments when that lowers risk.** One increment
   may address several tightly coupled edits. Do not force unrelated naming,
   packaging, or style work into it.
6. **Compare the result with the original pain.** Verify affected callers and
   remove obsolete paths when safe. Stop when the requested improvement is
   demonstrated; commit or ship only when requested.

## Diagnostic patterns

| Observation | Question | Possible move |
| --- | --- | --- |
| One fact or policy is maintained in several places | Which layer should own it? | Consolidate and derive secondary views |
| A small change touches unrelated modules | Is responsibility fragmented? | Move behavior to the owning boundary |
| Tests require broad mocking | Is the interface wider than the capability? | Narrow or invert the dependency |
| A module changes for unrelated reasons | Are multiple responsibilities merely colocated? | Extract along an established change axis |
| Callers repeatedly translate the same primitive data | Is a domain contract missing? | Introduce a value or interface when reuse is real |
| Build or runtime cost dominates iteration | Where does measurement place the cost? | Optimize or isolate the measured boundary |

These are prompts for investigation, not numeric thresholds or automatic
refactors.

## Larger migrations

Use parallel old and new paths only when incremental routing materially reduces
risk. Define compatibility and rollback boundaries, migrate callers in bounded
steps, then remove the old path after evidence shows it is unused. A direct
refactor is simpler when coexistence adds no safety.

## Red flags

- Redesign without a named problem or affected caller.
- A new abstraction with no owned responsibility or credible reuse.
- Metrics chosen because they are easy to count rather than relevant.
- Behavior, compatibility, or user changes lost during structural cleanup.
- A permanent duplicate path created as a temporary migration mechanism.

## Verification

Show that relevant tests or probes pass, affected callers use the intended
owner, obsolete duplication is gone or explicitly staged for removal, and the
original architecture pain improved. State any unverified integration or
migration risk.
