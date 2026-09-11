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
5. **Implement** in the current codebase; keep any reference checkout untouched.
6. **Verify against the CURRENT project's gates**, its tests/compiler/lint/CI, never
   the reference's own tests alone. Record provenance and license obligations in
   the PR's Reference/Prior-Art section.

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

## References

- `references/contract.md`, reference kinds, authority, retention and licensing
- `../cross-repo-source/README.md`, indexed and external source retrieval
- `../push-pr/README.md`, PR creation records the Reference/Prior-Art section
- `../web-reference/references/storage.md`, web capture layout
