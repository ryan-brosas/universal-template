---
name: reference-driven-development
description: "Use when implementation should be grounded in outside prior art, adapting an external implementation, comparing against a reference repository, or porting a known pattern into the current codebase."
---

# Reference-Driven Development

## Core Principle

When outside code materially reduces uncertainty, use ONE strong reference repository at `<project>/reference/<repo>/`, read its actual source and direct tests, compare boundaries, adopt/adapt/omit deliberately, and verify against the CURRENT project's gates. Never blind-copy; never mass-ingest.

## When to Use / NOT

- **Use when:** adapting an external implementation; comparing against a reference repo; porting a known pattern; the user points at an upstream implementation to follow.
- **Use when:** a relevant project-local code reference at `reference/<repo>/` or web reference at `reference/web/<site>/` already exists and consulting it would materially reduce implementation uncertainty (even without an explicit "use this as inspiration" request).
- **NOT when:** ordinary implementation where current project source, nearest implementation, and mechanical verification are enough; global `AGENTS.md` owns that default posture. This skill activates when outside prior art enters the loop.

## Workflow

1. **Ground locally**, inspect the current project and identify the seam; decide whether outside code materially reduces uncertainty (if not, stop, implement directly).
2. **Notice existing references**, if `reference/` or `reference/web/` exists, scan top-level names and open only candidates relevant to the seam (bounded listing, not bulk ingestion).
3. **Select the reference**, place or reuse it at the conventional path. Code references: ONE strong repository at `<project>/reference/<repo>/`; add a second only after naming the gap the first left. Web references: synthesis may combine several captured sites when each contributes a named quality. Full rules: `~/.agents/references/reference-contract.md` (kinds, authority, defaults, licensing, lifecycle).
4. **Check freshness when it matters**, for a git checkout reference, note current revision and upstream state (`git -C reference/<repo> status`, `git -C reference/<repo> log -1 --oneline`); do not destructively update a dirty reference.
5. **Read it as code, not docs**, map with Fovea (explicit root) when helpful; read the exact source and its direct tests; Steroid when exact semantics add value.
6. **Compare boundaries**, local vs reference; decide ADOPT / ADAPT / OMIT per concern; never blind-copy.
7. **Implement** in the current codebase; keep the reference untouched (read-only checkout).
8. **Verify against the CURRENT project's gates**, its tests/compiler/lint/CI, never the reference's own tests alone. Record provenance and license obligations in the PR's Reference/Prior-Art section.

## Reference sources

A reference source is usually a repository, but the loop is the same for other evidence:

- **Repository**: `reference/<repo>/`; code and tests, acquired as a read-only clone.
- **Website**: `reference/web/<site>/`; rendered visual and interaction evidence, captured by `web-reference`. This skill only consumes it.
- **Design artifact**: an approved design state (for example an OpenDesign project); it becomes implementation evidence only after explicit approval.

For a web reference, read `REFERENCE.md` first, then `manifest.json` for scope
and coverage gaps. A partial capture is not complete knowledge. Site captures
never become foundations (see the reference contract).

## Rules

1. **Examples beat specs**, 1–2 concrete examples from the reference one-shot what a spec takes pages to describe.
2. **The reference is prior art, not authority**, the current project's requirements and gates decide.
3. **One code reference at a time**; frontend synthesis may read several web references, each for a named quality.
4. **A reference repository is never converted** into a foundation skill, index, or corpus by default.
5. **Licensing obligations** are recorded when materially copying.

## Red Flags

- Blind-copying reference code past the local boundary.
- Turning the reference into an index/corpus/foundation by default.
- Skipping local verification because the reference's tests passed.
- Treating this skill as the default implementation posture, it is not.

## Verification

- Reference checkout exists at the conventional path; provenance + license recorded.
- The ADOPT/ADAPT/OMIT decision is stated per concern.
- Changes verified against the current project's gates (named check + exit code).

## References

- `~/.agents/references/reference-contract.md`, canonical reference-checkout contract
- `../push-pr/SKILL.md`, PR creation records the Reference/Prior-Art section
