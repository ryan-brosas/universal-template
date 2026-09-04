# Elm style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `elm-style-*.md` capsules, `elm-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Elm Style Guide (official)](https://elm-lang.org/docs/style-guide) (primary) | clean diffs over compactness; ≤80 cols; descriptive qualified names; top-level type annotations; body on next line; two blank lines between top-level defs; simple union/alias layout |
| [NoRedInk Elm Style Guide](https://github.com/NoRedInk/elm-style-guide) (secondary) | `elm-format`; exhaustive case; custom types over string aliases for IDs; avoid giant `let`; no single-step pipe; `_ ->` over `always`; parens over `<|` |
| [Elm Guide — Modules](https://guide.elm-lang.org/webapps/modules.html) (secondary) | modules around central type; minimal `exposing`; `src/` layout; qualified imports |

**Not duplicated here:** Full TEA architecture — use stack capsules in `skills/*-foundation`. Every Html/CSS rule — see frontend skills.

## Mental model

Elm style optimizes for **regularity and compiler-aided safety**:

1. **Mechanical** — `elm-format` on every change; ≤80 columns when feasible.
2. **Declarations** — type-annotate top-level; body on following line; two blank lines between defs.
3. **Names** — descriptive; qualified (`List.map` not bare `map`); custom types for domain IDs.
4. **Types** — simple indentation; constructors on own lines; avoid aligned-column mania.
5. **Modules** — one central type per module; narrow `exposing`; files under `src/`.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Format | `elm-format` / `mix format`-equivalent for Elm |
| Line length | ≤80 preferred |
| Top-level spacing | two blank lines between declarations |
| Body | always on line after `=` |
| Types | one constructor/field per line; no trailing-comma alignment games |

### Naming & imports

| Entity | Convention |
|---|---|
| Functions/vars | descriptive snake_case (Elm convention) |
| Types | PascalCase |
| Imports | qualified by default; minimal `exposing` |
| Html | `exposing (..)` acceptable exception |
| IDs | `type UserId = UserId String` not `type alias` |

### Expressions

| Case | Rule |
|---|---|
| Pipe | multi-step only; subject leftmost |
| Case | exhaustive patterns; `case` before branches visually clear |
| Let | split large `let` into top-level helpers |
| Application | parens over `<|` chains |
| Anonymous | `\_ ->` over `always` |

### Modules

| Topic | Rule |
|---|---|
| File | `src/Module/Name.elm` mirrors module name |
| Focus | module centered on one custom type |
| Expose | list only public API; `@moduledoc false` N/A (use module doc string) |
| Decoders | co-locate with decoded type |

## Anti-patterns

- Unformatted source
- Missing top-level type annotation
- Inline `case` on same line as function head
- Column-aligned union types that reshuffle on rename
- `type alias` for nominal IDs (UserId as String)
- Catch-all `_` when new constructors expected
- Single-step `|>`
- Bare `union` instead of `Set.union`
- Abbreviated names (`accdns`)
- Giant `let` blocks instead of named functions
- `exposing (..)` on many imports

## Skill trace

| Artifact | Role |
|---|---|
| `elm-style-formatting-layout.md` | elm-format, 80 cols, declaration layout |
| `elm-style-naming-modules.md` | names, imports, module focus |
| `elm-style-types-declarations.md` | unions, aliases, custom types |
| `elm-style-pipelines-expressions.md` | pipe, case, let, application |
| `elm-coding-practices/SKILL.md` | elm-format/elm-review/test in CI |
