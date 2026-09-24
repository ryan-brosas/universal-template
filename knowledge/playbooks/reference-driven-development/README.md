---
title: reference-driven-development
summary: 'Use when outside prior art reduces uncertainty: adapting an external implementation, porting a pattern, or when a relevant project-local reference/<repo>/ or reference/web/<site>/ already exists and would materially help.'
kind: playbook
---

# Reference-Driven Development

## Core Principle

When outside code materially reduces uncertainty, start with ONE strong source,
read its actual code and direct tests, compare boundaries, adopt/adapt/omit
deliberately, and verify against the CURRENT project's gates. If a project-local
checkout at `<project>/reference/<repo>/` helps, use it; accessible source needs no
checkout or index. Never blind-copy; never mass-.

## When to Use / NOT

- **Use when:** adapting an external implementation; comparing against a
  reference repository; porting a known pattern; the user points at an upstream
  implementation to follow.
- **Use when:** a relevant project-local code reference at `reference/<repo>/` or
  web reference at `reference/web/<site>/` already exists and consulting it would
  materially reduce implementation uncertainty.
- **NOT when:** ordinary implementation where current project source, the nearest
  implementation, and mechanical verification are enough; global `AGENTS.md` owns
  that default posture.

## Workflow

For research-only requests, use the discovery and comparison steps, then return
findings. The implementation steps apply only when implementation is authorized;
see [research and ingestion scope](../cross-repo-source/README.md#inspiration-and-adaptation).

1. **Ground locally**, inspect the current project and identify the seam; decide
   whether outside code materially reduces uncertainty (if not, stop and
   implement directly).
2. **Find the source** with the cheapest sufficient capability: an indexed
   repository via `../cross-repo-source/README.md`, GitHub or equivalent
   discovery for source outside the corpus, or an existing project-local
   `reference/<repo>/` checkout. Reading accessible source implies no clone,
   checkout, or index.
3. **Read it as code, not docs**, read the exact source and its direct tests, and
   note the revision the evidence came from.
4. **Compare boundaries**, local vs reference; decide ADOPT / ADAPT / OMIT per concern.
   For projected state, trace every writer and the final consumer, not just the
   reducer helpers. A helper's ordering or equality rule need not match the
   composed UI/API, and a native-state mirror may also receive local writes.
   Preserve these observed contracts without prescribing an untested representation.
5. **Implement** in the current codebase; keep any reference checkout untouched.
6. **Verify against the CURRENT project's gates**, its tests/compiler/lint/CI, never
   the reference's own tests alone. Record provenance and license obligations in
   the PR's Reference/Prior-Art section.

## Differential comparison

A port's own tests encode the same expectation as the port, so a wrong expectation
survives both: the tests assert that a tool run keeps its accumulated argument text
and the port is written to keep it. The reference implementation does not share the
assumption, so run it.

When the reference is runnable from your toolchain, drive the reference and the port
with the same inputs, step by step, and compare observable state *after every step*,
not only the final result. Observed 2026-09-18 while porting a session reducer:
26 of 36 step comparisons differed on the first run, including a field the reference
drops when a run starts executing and an event its reducer ignores entirely. The
port's own tests had asserted the opposite in both cases, and passed.

- Compare the model's distinctions, not a lossy rendering of them. A comparator that
  renders a missing field as an empty one cannot see a dropped field, which is the
  class of divergence it exists for.
- Normalize representational differences explicitly, narrowly and once, in the
  harness header: a difference you state is a decision, one you collapse silently is
  a blind spot.
- Keep one reference/port pair per run when the reference numbers its own records
  (notice ids, sequence counters); a fresh pair per step compares different counters.
- Verify the comparator by mutation: make the port differ deliberately, confirm the
  run turns red, then remove the mutation. A green harness of unknown power is not
  evidence of parity.

## Reference sources

A reference source is usually a repository, but the loop is the same for other evidence:

- **Repository**: actual source and tests, read live (indexed or fetched) or from a
  read-only `reference/<repo>/` checkout.
- **Website**: `reference/web/<site>/`; rendered visual and interaction evidence,
  captured by `web-reference`. This skill only consumes it.
- **Design artifact**: an approved design state (for example an OpenDesign
  project); it becomes implementation evidence only after explicit approval.

For a web reference, read `REFERENCE.md` first, then `manifest.json` for scope
and coverage gaps. A partial capture is not complete knowledge.

## Rules

1. **Examples beat specs**, 1-2 concrete examples from the reference one-shot what a spec takes pages to describe.
2. **The reference is prior art, not authority**, the current project's requirements and gates decide.
3. **One code reference at a time**; frontend synthesis may read several web references, each for a named quality.
4. **Never convert a reference into permanent template content.** Do not distill a
   studied repository into a summary, index, or corpus; retrieve it again when
   needed, because source is cheap to re-fetch and summaries go stale.
5. **Licensing obligations** are recorded when materially copying.

## Red Flags

- Blind-copying reference code past the local boundary.
- Turning the reference into a summary, index, or corpus by default.
- Skipping local verification because the reference's tests passed.
- Treating this skill as the default implementation posture; it is not.

## Verification

- Relevant source was inspected; provenance + license recorded. A checkout path is
  required only when a checkout was used.
- The ADOPT/ADAPT/OMIT decision is stated per concern.
- Changes verified against the current project's gates (named check + exit code).
- A differential harness reports its comparison count with no differences, and a
  temporary mutation of the port or the comparison turns it red before that check is
  trusted as evidence.

## References

- `references/contract.md`, reference kinds, authority, retention and licensing
- `../cross-repo-source/README.md`, indexed and external source retrieval
- `../push-pr/README.md`, PR creation records the Reference/Prior-Art section
- `../web-reference/references/storage.md`, web capture layout
