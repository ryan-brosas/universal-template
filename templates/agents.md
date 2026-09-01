---
purpose: Source template for project-local AGENTS.md (/init or bootstrap).
updated: 2026-09-01
---

# AGENTS.md template

Render only repository-specific facts the model cannot cheaply infer from the
tree. Global defaults live in the user's global `AGENTS.md`; do not restate them.

## How to render

1. Discover and run real build/test/lint commands before naming them.
2. Pick one canonical verification command when the repo has one.
3. Record non-obvious invariants, generated files, traps, and project-specific
   dangerous operations only when verified.
4. Omit empty sections. Link durable context (e.g. `docs/project-context.md`)
   instead of duplicating it.

Do not copy generic coding doctrine, router skills, or examples from other repos.

---

# Agent Rules

## Check

```sh
[verified check command]
```

[What it runs, what green proves, restart/build notes if any.]

## Project rules

- [Non-obvious invariant with file, test, or workflow evidence.]
- [Generated-file ownership / regeneration command, if any.]
- [Compatibility, packaging, or security boundary the repo enforces.]

## Traps

- [Cache key, migration step, deploy difference, or local-only behavior.]

Omit when none verified.

## Dangerous project operations

- [Production, data, credential, or infra boundary specific to this repo.]

Omit when none beyond global defaults.
