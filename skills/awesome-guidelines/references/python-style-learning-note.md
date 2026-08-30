# Python style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `python-style-*.md` capsules, `python-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [PEP 8](https://peps.python.org/pep-0008/) | 4-space indent, 79/72 lines (99 team exception), import grouping, naming (`snake_case`, `CapWords`, `_` internal), whitespace, trailing commas, programming recommendations (`isinstance`, empty seq truthiness) |
| [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) | pylint/ruff gate, import modules not symbols (typing exemptions), full package paths, exception rules, no mutable defaults, comprehension limits, 80 cols + implicit join, type-annotate public APIs, `main()` guard |

**Not duplicated here:** Django/FastAPI/Pydantic stack patterns — use `foundation-pack/*-foundation` skills when the stack is known.

## Mental model

Python style serves **readability at review time**: consistency within a project beats PEP literalism when they conflict (PEP 8 “hobgoblin” clause). Two layers:

1. **Surface (PEP 8)** — layout, whitespace, naming shapes, import order. Tools (Ruff, Black/Pyink, pylint) enforce mechanically.
2. **Semantics (Google language rules)** — imports expose modules; exceptions are narrow; mutable defaults are forbidden; public APIs get types; scripts use `if __name__ == '__main__'`.

Catalog default: **PEP 8 + Google language rules**, with line length 88/100 only when the project formatter config says so (Black default 88 vs PEP 79 vs Google 80 — document project wins).

## Decision tables

### Layout & imports

| Topic | Rule |
|---|---|
| Indent | 4 spaces; no tab/space mix |
| Line length | 79 PEP stdlib; 80 Google; teams may use 88/99 with formatter |
| Wrap | parentheses/brackets implicit join; break before binary ops (Knuth) |
| Imports | stdlib → third-party → local; blank line between groups |
| Import style (Google) | `import module` / `from pkg import module`; not `from pkg.module import Class` except typing/`collections.abc` |
| Relative imports | PEP allows; Google prefers absolute full package |
| Wildcard | avoid `from x import *` |

### Naming (public vs internal)

| Entity | Public | Internal |
|---|---|---|
| module/package | `lower_with_under` | `_lower_with_under` |
| class | `CapWords` | `_CapWords` |
| function/method | `lower_with_under()` | `_lower_with_under()` |
| constant | `CAPS_WITH_UNDER` | `_CAPS_WITH_UNDER` |
| exception | `SomethingError` | — |

Avoid single-char names except `i/j/k`, `e` in except, `f` in `with open`. No `-` in module filenames.

### Exceptions & control flow

| Case | Rule |
|---|---|
| Preconditions | `raise ValueError` / built-ins — not `assert` for user-facing validation |
| `assert` | debug-only; removable without breaking logic |
| Catch | never bare `except:` or broad `except Exception:` unless re-raise or top-level isolation |
| `try` body | minimal lines |
| Cleanup | `with` preferred over manual close |
| Truthiness | `if seq:` not `len(seq)`; `if x is None:` not `if x == None` |
| Mutable default | **never** `def f(a=[])` — use `None` + assign inside |

### Types & entrypoints

| Case | Rule |
|---|---|
| Public API | annotate parameters and returns |
| `__init__` | return annotation usually omitted |
| `self`/`cls` | annotate only when needed (`Self`) |
| Script | `main()` + `if __name__ == '__main__':` — no side effects at import time |

### Source conflicts

| Topic | PEP 8 | Google | Catalog |
|---|---|---|---|
| Line length | 79 (99 team ok) | 80 strict | follow project formatter |
| Relative imports | acceptable | discouraged | absolute for new code |
| Shorthand / comprehensions | — | no multi-`for` in one comprehension | prefer readable loops when nested |

## Anti-patterns

- `def append(x, bucket=[]): bucket.append(x)`
- `except Exception: pass`
- `assert user_id, 'required'` for API validation
- Top-level `connect()` at import
- `from mymodule import MyClass` for app code (Google)
- `if len(items) == 0:`
- Mutable global module state without `_` + justification

## Skill trace

| Artifact | Role |
|---|---|
| `python-style-layout-imports.md` | indent, wrap, imports |
| `python-style-naming-modules.md` | naming table, filenames |
| `python-style-exceptions-truthiness.md` | errors, assert, if/seq/None |
| `python-style-defaults-types-main.md` | mutable defaults, annotations, main |
| `python-coding-practices` | application skill |
