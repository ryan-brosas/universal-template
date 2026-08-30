---
name: reference-driven-development
description: "Use when implementation should be grounded in outside prior art — adapting an external implementation, comparing against a reference repository, or porting a known pattern into the current codebase."
---

# Reference-Driven Development

## Core Principle

When outside code materially reduces uncertainty, use ONE strong reference repository at `<project>/reference/<repo>/` — read its actual source and direct tests, compare boundaries, adopt/adapt/omit deliberately, and verify against the CURRENT project's gates. Never blind-copy; never mass-ingest.

## When to Use / NOT

- **Use when:** adapting an external implementation; comparing against a reference repo; porting a known pattern; the user points at an upstream implementation to follow.
- **NOT when:** ordinary implementation — source-first reading, nearest implementation, and mechanical verification are the default posture owned by global `AGENTS.md`, not a skill invocation. This skill exists only when outside prior art enters the loop.

## Workflow

1. **Ground locally** — inspect the current project and identify the seam; decide whether outside code materially reduces uncertainty (if not, stop — implement directly).
2. **Select ONE reference** — place or reuse it at `<project>/reference/<repo>/`. Do not search ten repositories when one closes the gap. Full rules: `references/reference-contract.md` (purpose, location, authority, one-reference default, licensing, lifecycle).
3. **Read it as code, not docs** — map with Fovea (explicit root) when helpful; read the exact source and its direct tests; Steroid when exact semantics add value.
4. **Compare boundaries** — local vs reference; decide ADOPT / ADAPT / OMIT per concern; never blind-copy.
5. **Implement** in the current codebase; keep the reference untouched (read-only checkout).
6. **Verify against the CURRENT project's gates** — its tests/compiler/lint/CI, never the reference's own tests alone. Record provenance and license obligations in the PR's Reference/Prior-Art section.

## Rules

1. **Examples beat specs** — 1–2 concrete examples from the reference one-shot what a spec takes pages to describe.
2. **The reference is prior art, not authority** — the current project's requirements and gates decide.
3. **One reference at a time.**
4. **A reference repository is never converted** into a foundation skill, index, or corpus by default.
5. **Licensing obligations** are recorded when materially copying.

## Red Flags

- Blind-copying reference code past the local boundary.
- Turning the reference into an index/corpus/foundation by default.
- Skipping local verification because the reference's tests passed.
- Treating this skill as the default implementation posture — it is not.

## Verification

- Reference checkout exists at the conventional path; provenance + license recorded.
- The ADOPT/ADAPT/OMIT decision is stated per concern.
- Changes verified against the current project's gates (named check + exit code).

## References

- `references/reference-contract.md` — canonical reference-checkout contract (via the catalog `references/` directory)
- `../push-pr/SKILL.md` — PR creation records the Reference/Prior-Art section
