# C style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `c-style-*.md` capsules, `c-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [CMU C Coding Standard](https://users.ece.cmu.edu/~eno/coding/CCodingStandard.html) (primary) | snake_case names; verb function names; `g_` globals; Yoda comparisons; K&R braces; 78-char lines; initialize all variables; header guards; no data in `.h`; macro safety; explicit error checks; short functions; layering |
| [Linux kernel coding style](https://www.kernel.org/doc/html/latest/process/coding-style.html) (secondary) | descriptive global names; `*` binds to variable; short functions; limit typedef abuse; check every error path; project-specific indent (kernel: 8-tab) |

**Not duplicated here:** GNU coding standards (blocked at fetch time) — kernel style covers overlapping portability themes. Full Doxygen layout — use project doc generator.

**Project precedence:** kernel/embedded trees may mandate tabs, 80 columns, and SPDX headers — follow local `AGENTS.md` when it conflicts with CMU defaults.

## Mental model

Portable C style optimizes for **reader safety in a dangerous language**:

1. **Names reveal scope** — snake_case locals; `g_` globals (avoid); `ALL_CAPS` macros/constants; units in names (`timeout_msecs`).
2. **Headers are declarations only** — include guards; no variable definitions in `.h`; `extern` in header, definition in one `.c`.
3. **Control flow is explicit** — Yoda equality (`6 == x`); explicit predicate tests; braces on multi-line `if`/`while`; document intentional fallthrough.
4. **Macros are last resort** — parenthesize; `do { } while (0)` for multi-statement; prefer `static inline` for small helpers when C99+.
5. **Fail loudly** — initialize every variable; check `malloc`/syscall returns; named constants instead of magic numbers.

## Decision tables

### Naming

| Entity | Convention |
|---|---|
| Functions | snake_case verbs (`check_for_errors`) |
| Locals / params | snake_case (`error_count`) |
| Globals | `g_` prefix; avoid when possible |
| Constants / macros | `ALL_CAPS` with `_` |
| Structs | snake_case type; members ordered by size/alignment |
| Pointers | `char *name` — `*` with variable |
| Predicates | `is_*` prefix; explicit `== 0` / `!= 0` when not obvious |

### Files & headers

| Topic | Rule |
|---|---|
| Extensions | `.c` source, `.h` header |
| Guards | `#ifndef package_file_h` (no leading/trailing `_` for C++ interop) |
| Definitions | one `.c` owns globals; `extern` in `.h` |
| Includes | document why; group by subsystem |
| Layering | adjacent layers only; document violations |

### Formatting

| Topic | Rule |
|---|---|
| Braces | K&R — opening brace same line for control flow |
| Line length | ≤78 chars (CMU); 80 common in kernel |
| Statements | one per line; one variable per declaration |
| Comparisons | constant on left for `==` / `!=` |
| `switch` | `default` present; comment fallthrough; block scope for locals |

### Safety

| Topic | Rule |
|---|---|
| Init | every variable initialized at declaration |
| Errors | check syscall/`malloc`/library returns unless deliberately ignored |
| Magic numbers | `#define`, `const`, or `enum` with meaningful names |
| Macros | wrap args in `()`; no side-effect args; unique prefixed names |
| `goto` | rare; label left-aligned; comment purpose |

## Anti-patterns

- `char* a, b` (only first is pointer)
- Uninitialized stack variables
- Data definitions in header files (multiple definition / ODR surprises)
- `#ifdef DEBUG` without value — prefer `#if DEBUG`
- Magic bare integers in control flow
- Macro functions without parenthesized parameters
- Implicit truth tests on function returns that may change sentinel
- Abbreviated global names (`cntusr`)
- Heavy typedef of structs/pointers without opacity need

## Skill trace

| Artifact | Role |
|---|---|
| `c-style-formatting-control.md` | braces, line length, Yoda, switch |
| `c-style-naming-types.md` | snake_case, globals, pointers, structs |
| `c-style-headers-modules.md` | guards, extern, layering, no `.h` data |
| `c-style-macros-safety.md` | macros, init, errors, constants |
| `c-coding-practices/SKILL.md` | clang-format/cppcheck/splint in CI |
