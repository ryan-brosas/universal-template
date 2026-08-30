# Racket style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `racket-style-*.md` capsules, `racket-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [How to Program Racket: a Style Guide](https://docs.racket-lang.org/style/index.html) — Textual Matters, Choosing the Right Construct, Units of Code, Testing (primary) | DrRacket indent; closing parens on last line; 102 cols; no tabs; kebab-case names; `?`/`!`/`%` conventions; `define` over `let`; `cond`/`match` over `if`; `for/*` traversals; provide/contract-out top; top-down modules; rackunit test submodules |
| [Racket Basics and Style (course summary)](https://www.cs.umb.edu/~stchang/cs450/s25/racketbasics.html) (secondary) | provide before require; `[` for cond readability; `;;` vs `;`; predicate `?`; no magic numbers |

**Scope:** Standard `#lang racket` modules and packages. Typed Racket / Scribble have documented exceptions in the official guide.

## Mental model

Racket style optimizes for **DrRacket-shaped readability + explicit module boundaries**:

1. **Textual** — DrRacket indentation; parens on closing line; ≤102 columns; no tabs/trailing space.
2. **Naming/constructs** — kebab-case words; type-prefix functions; prefer `define`, `cond`/`match`, `for/*`.
3. **Modules** — purpose statement; provide/require sections; `contract-out`; top-down organization; small units.
4. **Verify** — rackunit `(module+ test …)`; `raco test`; precise `with-handlers`; `parameterize` for dynamic scope.

## Decision tables

### Textual layout

| Topic | Rule |
|---|---|
| Indent | DrRacket style (repo files pass "indent all") |
| Parens | closers on last line of form (not C-style own line) |
| Width | ≤102 chars; `;;` ruler lines for sections |
| Tabs | forbidden |
| if | each alternative on own line when multiline |
| Args | one line unless long → one arg per line |
| Comments | `;` inline, `;;` line-start; `#;` toggle expr |
| EOF | newline at end; no trailing whitespace |

### Naming & constructs

| Entity | Convention |
|---|---|
| Identifiers | English words with `-` (kebab-case) |
| Functions | verb/type-prefix (`board-serialize`) |
| Predicates | `?` suffix (`empty?`) |
| Mutators | `!` suffix |
| Classes | `%` suffix (`game-state%`) |
| Avoid | camelCase, `_` in names (except `_` placeholder) |
| Definitions | prefer `define` over nested `let` when feasible |
| Conditionals | `cond`/`match`/`case` over nested `if` |
| Loops | `for/list`, `for/fold`, etc. over manual `foldr`+lambda |
| Lambdas | named `define` for multi-line; short lambda OK in `map`/`filter` |
| Macros | functions first; macros only when necessary |
| Structs | fixed-field records; not ad-hoc long lists |

### Modules & contracts

| Case | Rule |
|---|---|
| Header | one-line purpose statement |
| Order | provide (with comments) → require → implementation |
| Exports | explicit `(provide …)` not `(all-defined-out)` |
| Contracts | `contract-out` on exports; type-like predicates minimum |
| Organization | top-down: important functions first |
| Size | aim ~500 lines/module; ~66 lines/function screen |
| Tests | `(module+ test …)` at end; `raco test file.rkt` |
| Parameters | `parameterize` not manual save/restore |

### Testing & errors

| Case | Rule |
|---|---|
| Debug | write failing test first, then fix |
| Handlers | precise predicates (`exn:fail:read?`), not `(lambda (_ #t) #t)` |
| Failures | `exn:fail?` not bare `exn?` (avoids catching breaks) |

## Anti-patterns

- Tab characters
- Lines >102 without break (unless file-local note)
- Closing `)` on its own line mid-form (C style)
- Non-DrRacket indentation
- camelCase / snake_case identifiers
- Underscores in regular names
- Nested `if` + `begin` where `cond`/`match` fits
- Heavy `let` where internal `define` works
- Long anonymous `lambda` instead of named helper
- Macro where function suffices
- `(provide (all-defined-out))`
- provide scattered through file bottom
- Missing purpose comments on exports
- 10k-line modules
- Manual parameter save/restore
- Catch-all exception handlers
- Graphical syntax boxes in source
- Plural module collection names (`contracts` vs `contract`)
- Magic numbers without named constants
- `attach()` (when applicable from ecosystem guidance)

## Skill trace

| Artifact | Role |
|---|---|
| `racket-style-formatting-textual.md` | indent, parens, width, comments |
| `racket-style-naming-constructs.md` | kebab-case, define/cond/for |
| `racket-style-modules-contracts.md` | provide, contract-out, size |
| `racket-style-testing-verify.md` | rackunit, handlers, parameterize |
| `racket-coding-practices/SKILL.md` | DrRacket indent + raco test in CI |
