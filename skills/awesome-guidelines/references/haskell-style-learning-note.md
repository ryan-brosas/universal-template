# Haskell style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `haskell-style-*.md` capsules, `haskell-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [HaskellWiki Programming guidelines](https://wiki.haskell.org/Programming_guidelines) (primary) | Haddock module header; ≤80 cols; no tabs/trailing ws; lowerCamelCase/UpperCamelCase; short functions; case layout; avoid partial functions; qualified Set/Map; hierarchical imports; separate IO; prefer data over synonyms; list comp sparingly; $ and . application |
| [Johan Tibbe Haskell Style Guide](https://github.com/tibbe/haskell-style-guide/blob/master/haskell-style.md) (secondary) | 4-space indent; where +2; blank line rules; explicit imports; Haddock on exports; strict fields `!`; lazy args strict only when needed; -Wall -Werror; guards over if |

**Not duplicated here:** Full GHC WorkingConventions — follow for GHC hacking. Every HLint rule — enable project config.

## Mental model

Haskell style is **readable equational code with explicit boundaries**:

1. **Layout** — 4 spaces, ≤80 columns, final newline, no trailing ws; case/guard alignment over brace syntax.
2. **Names & modules** — descriptive camelCase functions; UpperCamelCase types; Haddock on exports; explicit import lists; qualified containers.
3. **Functions** — few lines, one job; top-level type signatures; guards/patterns over `if`; avoid partial `head`/`fromJust`; moderate `$`/`.` and point-free.
4. **Types & effects** — prefer proper `data`/`newtype`; strict fields by default; lazy function args unless accumulator needs `!`; pure core separate from IO; `Text` over `String` in modern code.

## Decision tables

### File & layout

| Topic | Rule |
|---|---|
| Header | Haddock module block (Maintainer, Stability, description) |
| Line length | ≤80 (prefer 75); max ~100 only if unavoidable |
| Indent | 4 spaces; `where` +2; no tabs |
| Blank lines | one between top-level defs; none between sig and def |
| Case | break after `of`; align alternatives; avoid `{ ; }` style |
| Lambda | `\ t ->` with space after `\` |
| Module size | ~400 lines guideline |

### Naming & imports

| Entity | Convention |
|---|---|
| Functions/values | lowerCamelCase |
| Types/classes/ctors | UpperCamelCase |
| Infix ops | library code sparingly |
| Std imports | hierarchical (`Data.List`) |
| Set/Map | `import qualified Data.Map as Map` |
| Other libs | explicit import list or qualified |
| Modules | singular names (`Data.Map`) |

### Functions & control

| Case | Rule |
|---|---|
| Length | few lines; decompose large cases |
| Types | signature on every exported/top-level function |
| Partiality | document preconditions; `maybe`/`case` not bare `head` |
| if-then-else | prefer guards/patterns |
| List comp | short only; prefer `map`/`filter`/`foldr` |
| Application | `$` and `.` to reduce parens; spaces around `$` |
| Point-free | sparingly |
| Warnings | `-Wall -Werror` clean |

### Types, laziness, IO

| Topic | Rule |
|---|---|
| Data | prefer `data`/`newtype` over synonyms/tuples |
| Records | avoid direct ctor for large records; mind polymorphic fields |
| Fields | strict `!` default (Tibbe); UNPACK hot small fields |
| Function args | lazy unless strict accumulator recursion |
| IO | separate from pure modules; `let` not `<- return` |
| Strings | `Text`/`ByteString` over `String` in new code |
| Trace | debug only, not user feedback |
| Dead code | no commented-out blocks |

## Anti-patterns

- Tabs or trailing whitespace
- Lines >80 without refactor
- Missing Haddock on exports
- Blanket `import Module` without explicit list (non-Prelude)
- Unqualified `Map`/`Set` imports
- Partial `head`, silent `fromJust`
- Giant case on huge ADT (model smell)
- Type synonyms for long-lived domain types
- Class constraints on `data` declarations
- Lazy IO read+write same file
- `interact` and order-dependent IO
- Over-point-free unreadable pipelines
- Non-exhaustive/overlapping patterns ignored
- Lazy record fields without reason
- `String` in new library API

## Skill trace

| Artifact | Role |
|---|---|
| `haskell-style-formatting-layout.md` | indent, cols, case, blank lines |
| `haskell-style-naming-imports.md` | names, module header, imports |
| `haskell-style-functions-control.md` | sigs, partiality, guards, $ |
| `haskell-style-types-io.md` | strict data, newtype, IO split |
| `haskell-coding-practices/SKILL.md` | stylish-haskell/HLint/cabal test in CI |
