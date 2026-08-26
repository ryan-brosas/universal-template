---
name: codebase-driven-development
description: "Use when starting any implementation work: code is the ground truth, the session is the artifact, and you one-shot with examples; escalate to a spec only when the run outlives the session."
disable-model-invocation: true
---

# Codebase-Driven Development

The main discipline. Code is ground truth; markdown is post-code. A spec written before reading the code is a guess.

## Rules

1. **Code is ground truth.** Read the code that does the closest thing to what you want; it defines the real contract.
2. **The session is the artifact.** One-session work: the chat + diff IS the record. Don't burn it to markdown.
3. **Examples beat specs.** 1-2 examples from the codebase or an indexed inspiration repo one-shot what a spec takes pages to describe.
4. **Stack foundations.** Reuse proven code; encode it via `code-foundations` so the next run is a shortcut, not a re-derivation.
5. **Workflows live in skills.** Encoded ground truth makes even a cheap model mistake-free.

## Workflow

1. **Find the foundation** — route via `evidence-router` (Codebase Memory → CodeGraph Context → JetBrains → Fovea); run the /ship Inspiration gate: adopt / adapt / omit with provenance.
2. **Read the code** — the nearest feature, its tests, its callers. Tests are the executable spec.
3. **One-shot** — name the change as 1-2 concrete examples, implement the smallest slice (incremental-implementation, TDD).
4. **Verify** — run the named check; diff + passing check is the completion record.
5. **Stack** — if you just built a reusable primitive, encode it via `code-foundations`.
6. **Escalate only when the run outlives the session** — then burn it to a spec (spec-driven-development).

## Red Flags

- Spec written before reading the code.
- Re-deriving a pattern the codebase already encodes.
- Building a new foundation when a stacked one exists.

## Verification

- Change traces to code/examples, not prose.
- Nearest feature + tests read.
- Smallest slice verified by a named check.
- Spec written only when the run outlives the session.

## Skill Result Contract

```xml
<skill_result>
  <skill>codebase-driven-development</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Foundation found, code read, examples named, checks run</evidence>
  <artifacts>Diff + passing checks; spec only when escalated</artifacts>
  <risks>Spec drift, re-derived foundations, unverified claims, or none</risks>
</skill_result>
```
