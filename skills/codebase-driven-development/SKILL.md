---
name: codebase-driven-development
description: "Use when starting any implementation work: read current code first, map with Fovea when it helps, escalate semantics to Steroid, use one reference repository for prior art, implement in Fabric, and verify mechanically."
---

# Codebase-Driven Development

The lightweight default philosophy. Current source is ground truth; the session
and the diff are the record; every heavier layer is opt-in.

## Core Principle

Read the current code first; find the nearest implementation and tests; add a
heavier capability (Fovea, Steroid, a reference repository, Veda) only when it
closes a concrete gap; verify mechanically.

## When to Use / NOT

- **Use when:** starting any implementation work.
- **NOT when:** N/A — this is the default implementation posture. Heavier
  ceremonies (workflow-lifecycle, Schema enforce, foundation generation) are
  separate opt-ins.

## Workflow

1. **Read current code** — the feature you are changing, its neighbors, its
   tests. Tests are the executable spec.
2. **Map when it helps** — Fovea (`fovea_sketch` / `fovea_focus` /
   `fovea_impact`) for orientation or blast radius; skip it when direct
   reading is cheaper.
3. **Escalate semantics when it helps** — Steroid/JetBrains for exact types,
   usages, inheritance, inspections, or debugger evidence on non-trivial
   changes.
4. **One reference repository when prior art helps** — place or reuse it at
   `<project>/reference/<repo>/`, run Fovea on that root, and read the actual
   source and its direct tests (full workflow below).
5. **Adopt / adapt / omit** — compare the reference boundary with the local
   boundary; never blind-copy.
6. **Implement** — in normal Pi/Fabric code mode; Prewalk continues if armed.
7. **Verify mechanically** — the project's tests/compiler/lint/CI; the diff
   plus green checks is the completion record.
8. **Veda only when justified** — a stronger second opinion for hard
   architecture, subtle debugging, or high-risk review; advisory only.
9. **Capture selectively** — genuinely reusable *procedures* may become
   skills; implementation knowledge stays in code and reference repos.
10. **Persistent specs only when work really spans sessions or agents.**

## Reference workflow (prior art)

1. Inspect the current project; identify the local seam.
2. Decide whether outside code materially reduces uncertainty.
3. Select ONE strong reference repository and place it at
   `<project>/reference/<repo>/` (read-only, disposable). Prefer
   `.git/info/exclude` for local-only references instead of the shared
   `.gitignore`; a reference is not automatically committed, skilled, or
   indexed.
4. Map it with Fovea (explicit root) when helpful; read exact source and
   direct tests; use Steroid when exact semantics add value.
5. Compare boundaries, decide ADOPT / ADAPT / OMIT, and implement locally.
6. Verify against the CURRENT project's requirements and gates. When
   materially copying implementation, inspect the license and preserve
   required attribution.

## Rules

1. **Code is ground truth.** The code that does the closest thing defines the
   real contract.
2. **The session is the artifact.** Don't burn working context to markdown
   unless the work spans sessions or the user asks.
3. **Examples beat specs.** 1–2 concrete examples from the codebase or a
   reference repository one-shot what a spec takes pages to describe.
4. **One reference at a time.** Do not search ten repositories when one
   closes the gap.
5. **Gates judge outcomes.** No prose substitute for the mechanical check.

## Red Flags

- Spec or plan written before reading the code.
- Re-deriving a pattern the codebase (or a reference repository) already
  encodes.
- Turning a reference repository into a foundation skill, index, or corpus by
  default.
- Running every review surface (Fovea + Steroid + Veda + CI) for a tiny patch.

## Verification

- Change traces to code/examples, not prose.
- Nearest implementation + tests read; agreed scope verified by a named
  check.
- Reference-based changes verified against the current project's gates, not
  the reference's own tests alone.

## Skill Result Contract

```xml
<skill_result>
  <skill>codebase-driven-development</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Code read, examples named, reference decision recorded, checks run</evidence>
  <artifacts>Diff + passing checks</artifacts>
  <risks>Blind-copied reference code, re-derived patterns, or none</risks>
</skill_result>
```

## References

N/A — no reference files; this skill is self-contained.
