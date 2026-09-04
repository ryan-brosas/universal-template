---
name: elm-coding-practices
description: "Use when authoring or reviewing Elm, elm-format, 80-column layout, type annotations, qualified imports, custom ID types, multi-step pipelines, and elm-review/test in CI."
invocation: manual
disable-model-invocation: true
---

# Elm Coding Practices

Application skill for Elm style learning (from the archived `awesome-guidelines` style capsules). For TEA architecture and `Html` patterns, combine with stack capsules in `foundation-pack/`.

## Core Principle

Elm quality is **regular layout plus compiler support**, formatted mechanically, typed explicitly, modules focused on one custom type.

## When to Use / NOT

- Elm applications, packages, and `src/` modules.
- Setting up `elm-format`, `elm-review`, `elm-test` in CI.

**NOT when:**

- Generated `Page` boilerplate only, validate hand-edited modules.
- Non-Elm code.

## Workflow

1. **Layout**, elm-format, 80 cols, declaration shape (`elm-style-formatting-layout.md`).
2. **Modules**, names, imports, focus (`elm-style-naming-modules.md`).
3. **Types**, unions, IDs, decoders (`elm-style-types-declarations.md`).
4. **Expressions**, pipes, case, let (`elm-style-pipelines-expressions.md`).
5. **Verify**, `elm-format --validate`, `elm-test`, `elm-review` on changed modules.

## Red Flags

- Unformatted `.elm`
- Missing top-level type annotation
- Inline one-line `case` definitions
- Column-aligned type blocks
- `type alias` for nominal IDs
- Non-exhaustive `case` with `_`
- Single-step pipeline
- Unqualified `map`/`filter` imports
- Abbreviated function names
- Giant `let` instead of top-level helpers
- Widespread `exposing (..)`

## Verification

- `elm-format --validate`
- `elm-test` / `npm test` (project)
- `elm-review` (project rules)
- Capsule checklist on module `exposing` lists


## References

- `awesome-guidelines/references/elm-style-learning-note.md`
- `awesome-guidelines/references/elm-style-formatting-layout.md`
- `awesome-guidelines/references/elm-style-naming-modules.md`
- `awesome-guidelines/references/elm-style-types-declarations.md`
- `awesome-guidelines/references/elm-style-pipelines-expressions.md`
