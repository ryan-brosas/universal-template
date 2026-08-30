# Common Lisp style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `lisp-style-*.md` capsules, `common-lisp-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [lisp-lang.org style guide](http://lisp-lang.org/style-guide/) (primary) | lowercase lisp-case; `*dynamic*` / `+constant+`; `p`/`-p` predicates; 2-space indent; ≤100 cols; `;;;;` file header; docstrings; CLOS slot order + `:type`; when/unless; `:import-from` over `:use`; hierarchical packages; ASDF metadata; small libraries |
| [Google Common Lisp Style Guide](https://google.github.io/styleguide/lispguide.xml) (secondary) | Emacs/SLIME indentation; intent-based naming; no `::` in production; explicit `defgeneric`; avoid `slot-value` except low-level; comment semicolon levels; no abbreviations in names |

**Not duplicated here:** Full ASDF/Quicklisp setup tutorials — use project docs. Norvig/Pitman deep style — optional further reading.

## Mental model

Common Lisp style balances **Lisp tradition with maintainable libraries**:

1. **Names** — lowercase hyphenated words; `*special*` and `+constant+`; predicates `p`/`-p`; no package prefix in symbol names.
2. **Layout** — Emacs/SLIME indentation; 100-column lines; one blank line between top-level forms; `;;;;` file purpose comment.
3. **Packages** — hierarchical `project.module`; explicit `:import-from`; avoid `:use` except `:cl`; never `pkg::internal` in production.
4. **CLOS** — typed slots, readers, docstrings; `defgeneric` for exported protocols; accessors over `slot-value`.
5. **Control & docs** — `when`/`unless` for single branch; factor complex conditions; docstrings on public API.

## Decision tables

### Naming

| Entity | Convention |
|---|---|
| Functions/vars | `lower-case-with-hyphens` |
| Special vars | `*earmuffs*` |
| Constants | `+like-this+` |
| Predicates | `bluep` or `seatbelt-fastened-p` |
| Types/classes | same hyphen style (`request`, `http-request`) |
| Package symbols | no `myapp-parser-` prefix inside `myapp.parser` package |

### Files & packages

| Topic | Rule |
|---|---|
| Header | `;;;;` purpose; then `(in-package ...)` |
| Line length | ≤100 columns |
| Packages | one per file (usually); hierarchical names |
| Imports | `:import-from` specific symbols; avoid `:use` |
| Internals | export or split user/impl packages; no `::` in prod |

### CLOS

| Topic | Rule |
|---|---|
| Slots | accessor/reader, initarg, initform, type, documentation order |
| Types | `:type` on slots when possible |
| Protocol | `defgeneric` + documentation for exported GF |
| Access | readers/`with-accessors`; not `slot-value` in app code |

### Control & docs

| Case | Rule |
|---|---|
| Single branch | `when` / `unless` not bare `if` |
| Complex test | extract predicate function |
| Comments | `;;;;` file, `;;;` section, `;;` block, `;` end-of-line |
| Dead code | delete via VCS, don't comment out |

## Anti-patterns

- camelCase or snake_case symbols
- Abbreviated names (`user-cnt`, `mk-node`)
- Prefixing symbols with package name
- `:use :alexandria` importing everything
- `other-pkg::internal-symbol` in application code
- `slot-value` in domain logic
- Generic functions for unrelated overloads only
- Commenting out large blocks instead of deleting
- Missing docstrings on exported functions/classes
- Monolithic system with no library split

## Skill trace

| Artifact | Role |
|---|---|
| `lisp-style-formatting-files.md` | indent, columns, file header |
| `lisp-style-naming-symbols.md` | lisp-case, *, +, predicates |
| `lisp-style-packages-systems.md` | defpackage, ASDF, hierarchy |
| `lisp-style-clos-control.md` | CLOS, when/unless, conditions |
| `common-lisp-coding-practices/SKILL.md` | slime/sbcl lint, asdf test in CI |
