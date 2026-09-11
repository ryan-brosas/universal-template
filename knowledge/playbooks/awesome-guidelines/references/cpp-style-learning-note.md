# C++ style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `cpp-style-*.md` capsules, `cpp-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) (primary) | C++20 target; self-contained headers + IWYU; 2-space indent; PascalCase types/functions; snake_case variables; `kConstant`; class member trailing `_`; `unique_ptr` ownership transfer; no virtual in ctors; `explicit` conversions; short functions; namespaces snake_case |
| [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) (secondary) | RAII resource handles; raw pointer/reference non-owning; prefer return values over out-params; avoid naked `new`/`delete`; `not_null` intent; lambda capture discipline |

**Not duplicated here:** LLVM/Chromium/Mozilla variant guides — adopt project baseline when it diverges. NASA safety-critical rules — use when domain requires. Full cpplint rule list — run tool in CI.

## Mental model

Google C++ style manages **language power vs reader cost**:

1. **Headers are contracts** — every `.h` self-contained with guards; include what you use; minimize transitive includes.
2. **Names encode role** — PascalCase types/functions, snake_case locals/params, `k` constants, trailing `_` on class data members.
3. **Ownership is explicit** — transfer with `std::unique_ptr`; shared only when needed; raw pointers borrow; RAII everywhere.
4. **Classes stay predictable** — no virtual calls in constructors; no implicit conversions; prefer `struct` for passive data.
5. **Optimize for readers** — short functions, obvious control flow, 2-space indent, cpplint/clang-format in CI.

## Decision tables

### Files & headers

| Topic | Rule |
|---|---|
| Extensions | `.cc` sources, `.h` headers, `.inc` rare includes |
| Filenames | lowercase with `_` or `-`; specific names (`http_server_logs.h`) |
| Guards | `#ifndef PROJECT_PATH_FILE_H_` |
| Self-contained | header includes all dependencies; no `-inl.h` split |
| IWYU | include direct provider of every symbol used |

### Naming

| Entity | Convention |
|---|---|
| Types | PascalCase (`UrlTable`, `enum class UrlTableError`) |
| Functions | PascalCase (`AddTableEntry`); accessors may snake_case (`count()`, `set_count()`) |
| Variables / params | snake_case (`table_name`) |
| Class data members | snake_case + trailing `_` (`table_name_`) |
| Struct members | snake_case, no trailing `_` |
| Constants | `kMixedCase` (`kDaysInAWeek`) |
| Namespaces | snake_case, globally unique top-level |

### Ownership & memory

| Case | Rule |
|---|---|
| Exclusive heap | `std::unique_ptr`, move to transfer |
| Shared | `std::shared_ptr` when sharing is design requirement |
| Borrow | raw pointer/reference, non-owning, lifetime documented |
| Allocation | avoid naked `new`/`delete`; RAII wrappers |
| Out params | prefer return values / struct returns |

### Classes & functions

| Case | Rule |
|---|---|
| Constructors | no virtual calls; prefer factory if init can fail |
| Conversions | `explicit` on single-arg ctors and conversion operators |
| struct vs class | struct for passive data; class when invariants/behavior |
| Size | short functions; one logical operation |
| Parameters | const ref for large inputs; pass by value when cheap |

## Anti-patterns

- Transitive `#include` reliance
- `camelCase` locals or `snake_case` types in Google-style codebases
- Raw owning pointer passed without documented lifetime
- Virtual method invoked from constructor
- Implicit conversion constructors/operators
- Global mutable state without strong justification
- `-inl.h` template definition splits (deprecated pattern)
- Returning pointer/reference to local

## Skill trace

| Artifact | Role |
|---|---|
| `cpp-style-formatting-headers.md` | headers, guards, IWYU, layout |
| `cpp-style-naming-types.md` | PascalCase/snake_case/kConstant |
| `cpp-style-ownership-raii.md` | smart pointers, RAII, returns |
| `cpp-style-classes-api.md` | ctors, explicit, struct/class, functions |
| `cpp-coding-practices/SKILL.md` | clang-format/cpplint/clang-tidy in CI |
