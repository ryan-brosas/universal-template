# Dart style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `dart-style-*.md` capsules, `dart-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Effective Dart](https://dart.dev/effective-dart) — Style, Documentation, Usage, Design (primary) | UpperCamelCase types; lowerCamelCase identifiers; snake_case files/packages; dart format; 80 cols; /// docs; null-safety idioms; collection literals; async/await; typed public API; class modifiers; ==/hashCode |
| [Dart linter rules](https://dart.dev/tools/linter-rules) (secondary) | mechanical enforcement via `analysis_options.yaml` / `dart analyze` |

**Not duplicated here:** Every individual linter rule — enable project-relevant rules from Effective Dart links. Flutter widget layout — use stack capsules in `skills/*-foundation`.

## Mental model

Effective Dart optimizes for **consistency + brevity**:

1. **Style** — `dart format` is law; naming by construct kind; sorted imports; braces on all control flow.
2. **Documentation** — `///` on public API; one-sentence summary first; square-bracket references; no redundant getter/setter docs.
3. **Usage** — null-safe idioms; interpolation over concat; collection literals; tear-offs; async/await; specific catches.
4. **Design** — names read like sentences; prefer `final`; class modifiers for extend/implement control; full type annotations on public signatures.

## Decision tables

### Naming & layout

| Entity | Convention |
|---|---|
| Types/extensions | UpperCamelCase |
| Other identifiers | lowerCamelCase |
| Constants | prefer lowerCamelCase |
| Files/packages/dirs | lowercase_with_underscores |
| Import prefixes | lowercase_with_underscores |
| Format | `dart format`; ≤80 columns |
| Imports | dart: → package: → relative; alphabetical |

### Documentation

| Rule | Detail |
|---|---|
| Public API | `///` doc comments |
| Opening | single-sentence summary, own paragraph |
| Booleans | "Whether …" |
| Side-effect methods | third-person verb phrase |
| Value methods | noun / non-imperative phrase |
| Links | `[Identifier]` in scope |

### Usage idioms

| Case | Rule |
|---|---|
| Null | don't init to null explicitly; promotion/null-check |
| Strings | interpolation > concat |
| Collections | literals; `.isEmpty` not `.length == 0` |
| Functions | tear-off over lambda when equivalent |
| Fields | `final` read-only; initializing formals |
| Errors | `on Type catch`; `rethrow`; don't catch `Error` |
| Async | `async`/`await`; avoid pointless `async` |

### Design & types

| Case | Rule |
|---|---|
| Privacy | prefer private members |
| API names | consistent terms; positive booleans |
| Subclassing | class modifiers (`final`, `interface`, `sealed`) |
| Types | annotate public fields/returns/params when not obvious |
| Equality | override `hashCode` with `==`; avoid mutable equality |
| Constructors | const when possible; no `new` |

## Anti-patterns

- Leading `_` on non-private symbols
- Explicit `= null` initialization
- `.length` for emptiness check
- Unnecessary getter/setter wrappers
- Bare `catch (e)` swallowing errors
- Catching `Error` types
- `new` / redundant `const`
- Importing from other package's `src/`
- Public API without return type annotation
- Custom equality on mutable classes
- One-member abstract class instead of function typedef

## Skill trace

| Artifact | Role |
|---|---|
| `dart-style-formatting-names.md` | format, naming, imports |
| `dart-style-documentation.md` | /// docs, summaries |
| `dart-style-usage-idioms.md` | null, collections, async, errors |
| `dart-style-design-api.md` | types, classes, equality, naming |
| `dart-coding-practices/SKILL.md` | dart format/analyze/test in CI |
