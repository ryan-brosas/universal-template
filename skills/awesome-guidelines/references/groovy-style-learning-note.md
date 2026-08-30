# Groovy style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `groovy-style-*.md` capsules, `groovy-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Apache Groovy style guide](https://groovy-lang.org/style-guide.html) (primary) | no semicolons; optional return; no redundant `def`+type; omit `public`; parenless calls; POGO properties; named ctor params; `with`/`tap`; `==` vs `is()`; GStrings; native list/map/range/regex; GDK iterators; switch power; safe nav `?.`; Groovy truth; Elvis; assert; public API strong typing |
| [CodeNarc convention rules](https://codenarc.org/codenarc-rules-convention.html) (secondary) | `@CompileStatic` in performance libs; require method/field types in strict trees; no tab; ordering public-before-private |

**Not duplicated here:** Full Grails CodeNarc ruleset — enable project-relevant rules. Gradle plugin wiring — follow stack capsules in `foundation-pack/`.

## Mental model

Groovy style is **progressive idiomatic Groovy over Java paste**:

1. **Surface syntax** — drop semicolons and redundant `public`; omit useless `()`; prefer GStrings and native `[ ]` / `[ : ]` literals.
2. **Objects** — POGO properties over boilerplate getters; property access; named-parameter construction; `with`/`tap` for repeated mutation.
3. **Collections & control** — GDK `each`/`findAll`/`collect` over manual loops; powerful `switch`; Groovy truth; `?.` and `?:`.
4. **API contracts** — strong types on public surfaces; `def` only when IDE-inferred private helpers; assert preconditions; typed parameters for static checking.

## Decision tables

### Syntax & layout

| Topic | Rule |
|---|---|
| Semicolons | omit (idiomatic) |
| Return | omit on short methods/closures when last expr is result |
| `def` | never with explicit type; not on constructors |
| Visibility | omit `public`; mark non-public explicitly |
| Calls | omit parens for top-level/closure-last-arg forms |
| `.class` | omit suffix — use class literals directly |
| Strings | GStrings `"${x}"` for interpolation; single quotes for constants |
| Regex | slashy `/pattern/` strings |

### Objects & beans

| Case | Rule |
|---|---|
| Properties | POGO fields → generated accessors |
| Access | `obj.prop` not `getProp()` when Groovy-facing |
| Construction | `new Bean(name: x, cluster: y)` |
| Mutation block | `bean.with { … }` or `tap { … }` for builder return |
| Equality | `==` (null-safe equals); reference `is()` |
| Package scope | `@PackageScope` when needed |

### Collections & GDK

| Case | Rule |
|---|---|
| Literals | `[1,2]`, `[k: v]`, `1..10`, `~/re/` |
| Membership | `x in list` |
| Iteration | `each`, `findAll`, `collect`, `inject` |
| Switch | types, ranges, lists, closures |
| Truth | `if (name)` not null/empty double-check |
| Default | Elvis `name ?: 'Unknown'` |
| Null chain | `order?.customer?.address` |

### Typing & API

| Audience | Rule |
|---|---|
| Public API | explicit parameter and return types |
| Private helpers | `def` OK when type obvious to IDE |
| Parameters | typed — not `def param` in public methods |
| `def` return | beware accidental return of assignment expr |
| Preconditions | Groovy `assert` (always on) |
| Catch | `catch (Exception)` or typed; bare `catch (any)` only when intentional |
| Libraries (strict) | CodeNarc: types required, `@CompileStatic` when project mandates |

## Anti-patterns

- Java-style semicolons everywhere
- `def String x` redundant combo
- `public` on every class/method
- Empty `()` before trailing closure `each() { }`
- Java getter/setter boilerplate on POGOs
- String `+` concatenation when GString fits
- Manual null chains when `?.` works
- `==` for reference identity (use `is()`)
- Untyped public API (`def` methods) in shared libraries
- Returning assignment (`m2.c = 3`) accidentally from `def` methods
- Catching `any` when specific handling needed
- `Vector`/`Hashtable` (obsolete JDK types)

## Skill trace

| Artifact | Role |
|---|---|
| `groovy-style-syntax-idioms.md` | semicolons, def, parens, strings |
| `groovy-style-objects-properties.md` | POGOs, with/tap, equality |
| `groovy-style-collections-gdk.md` | literals, GDK, switch, truth, nav |
| `groovy-style-typing-api.md` | public typing, assert, CodeNarc |
| `groovy-coding-practices/SKILL.md` | CodeNarc/npm-groovy-lint/test in CI |
