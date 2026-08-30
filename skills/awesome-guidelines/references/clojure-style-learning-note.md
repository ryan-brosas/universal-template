# Clojure style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `clojure-style-*.md` capsules, `clojure-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [bbatsov/clojure-style-guide](https://github.com/bbatsov/clojure-style-guide) `README.adoc` (primary) | 2-space indent; ≤80–120 cols; gather trailing parens; one ns/file; comprehensive `ns` with `:require`; lisp-case names; `CapitalCase` types; `?` predicates; `!` side effects; `*earmuffs*` dynamics; idiomatic `when`/`if-let`/threading; keywords for map keys; vectors over lists; `ex-info`; `with-open`; macros only when needed |
| [Clojure contrib coding guidelines](https://clojure.org/community/contrib_howto#_coding_guidelines) (secondary) | name+signature stability; prefer function over macro; docstrings; `?` predicates; `_` ignored bindings; sequence composition over `loop/recur`; protocol extension ownership rules |

**Not duplicated here:** Full semantic-indentation debate — pick one style per project. Every macro/testing edge case — see source for exhaustive list.

## Mental model

Clojure style optimizes for **uniform Lisp readability**:

1. **Layout** — spaces not tabs; 2-space body indent; trailing parens gathered; one namespace per file.
2. **Namespaces** — multi-segment names; sorted `:require`; aliases over `:refer :all`; no `:use`.
3. **Naming** — lisp-case functions/vars; `CapitalCase` records/protocols; `?` / `!` / `*dynamic*` conventions.
4. **Expression idioms** — `when` for single branch; threading macros for pipelines; keywords as map keys; avoid index-based access.
5. **Safety** — `ex-info` + standard exceptions; `with-open`; catch specific types; function before macro.

## Decision tables

### Layout & files

| Topic | Rule |
|---|---|
| Indent | 2 spaces; no tabs |
| Line length | ≤80 preferred; ≤120 max by team agreement |
| Parens | gather trailing `)` on one line |
| Files | one `ns` per file; `project.module` naming |
| `ns` form | `:refer-clojure` / `:require` / `:import`; sort deps |

### Naming

| Entity | Convention |
|---|---|
| Namespace | `org.project.module`; kebab segments |
| Functions/vars | lisp-case (`parse-config`) |
| Types/protocols | `CapitalCase` (`HttpRequest`) |
| Predicates | end with `?` |
| Side effects | end with `!` |
| Dynamic vars | `*earmuffs*` |
| Constants | `+UPPER+` or idiomatic `k` names per project |

### Functions & idioms

| Case | Rule |
|---|---|
| Length | short; limit positional arity (~5) |
| Conditionals | `when` not single-branch `if`; `if-let`/`when-let` |
| Pipelines | `->` / `->>` / `as->` with aligned args |
| Vars | no `def` inside function bodies |
| Core shadow | never shadow `clojure.core` without `:refer-clojure :exclude` |
| `cond` | `:else` default branch |

### Data & errors

| Case | Rule |
|---|---|
| Collections | vectors/maps/sets over lists; keywords for map keys |
| Access | `(m :k)` or `(:k m)`; avoid `.get` index loops |
| Exceptions | `ex-info` or standard Java types; no custom types without reason |
| Resources | `with-open` not manual `finally` |
| Catch | specific exceptions; not `Throwable` |
| Macros | only when function cannot; document usage-first |

## Anti-patterns

- `:use` or `:refer :all` in new code
- Single-segment namespaces in libraries
- camelCase or snake_case function names
- `is-palindrome` / Java-style predicate names
- Lists for sequential data when vector suffices
- Index-based `nth` loops over seqs
- `def` inside functions for locals
- Macro where plain function works
- Catching `Throwable`
- Multiple namespaces in one file

## Skill trace

| Artifact | Role |
|---|---|
| `clojure-style-layout-namespaces.md` | indent, parens, ns form |
| `clojure-style-naming-types.md` | lisp-case, ?, !, dynamics |
| `clojure-style-functions-idioms.md` | when/if-let, threading, arity |
| `clojure-style-data-safety.md` | collections, ex-info, macros |
| `clojure-coding-practices/SKILL.md` | clj-kondo/cljfmt/test in CI |
