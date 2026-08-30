# JavaScript style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `javascript-style-*.md` capsules, `javascript-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html) | 2-space indent, 80 cols, semicolons, `const`/`let`, named exports only, `.js` in import paths, no mutable exports, `===` (+ `== null`), no `eval`/`with`, JSDoc on public API, K&R braces |
| [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) | ESLint-aligned rules: `prefer-const`, `eqeqeq`, no mutable exports, trailing commas, object spread, explicit string/number comparisons vs boolean shortcuts, semicolons/ASI hazards, no `var` |

**Not duplicated here:** TypeScript domain modeling — `typescript-coding-standards`. React/component patterns — `react-foundation`. HTML/CSS — `frontend-markup-practices`.

## Mental model

Modern JS style is **lint-enforced readability** plus **module boundary discipline**:

1. **Modules** — ES `import`/`export`; export only named symbols; do not mutate exported bindings; one import path per file aggregate.
2. **Variables** — `const` default, `let` when reassigned, never `var`; declare close to use.
3. **Equality & truthiness** — `===`/`!==`; allowed exception `x == null` for null+undefined; Airbnb: explicit checks for strings (`!== ''`) and counts (`length > 0`) when ambiguity matters.
4. **Format** — 2 spaces, semicolons, braces on all multi-line control flow, trailing commas in multiline literals.
5. **Safety** — no `eval`, `with`, non-standard language extensions, or primitive wrapper `new String()`.

## Decision tables

### Modules & exports

| Topic | Google | Airbnb | Catalog default |
|---|---|---|---|
| Default export | **banned** | preferred for single export | **named exports** (Google); project may document Airbnb exception |
| Wildcard import | `import * as foo` OK for namespaces | discouraged | namespace import when name collisions |
| Import path | include `.js` extension | bundler-dependent | follow project/bundler; Google closure style uses `.js` |
| Mutable export | forbidden | forbidden | getters/accessors instead |
| Duplicate imports | merge to one statement | merge to one statement | one path per file |

### Variables & equality

| Case | Rule |
|---|---|
| Declaration | `const` unless reassigned; one per declaration |
| Compare | `===`; `== null` / `!= null` OK for nullish |
| Boolean | `if (flag)` not `=== true` |
| String empty | `name !== ''` when distinguishing empty string |
| Array length | `items.length > 0` when 0 is meaningful |

### Formatting & control flow

| Topic | Rule |
|---|---|
| Indent | 2 spaces |
| Line length | 80 (Google); Prettier may differ — project wins |
| Braces | required except single-line `if` without else |
| Semicolons | always terminate statements |
| Literals | trailing comma when multiline |
| Switch | include `default` last (Google) |

### Disallowed / caution

| Feature | Verdict |
|---|---|
| `var` | never |
| `with`, `eval`, `Function(string)` | never (except loaders) |
| `new Array(n)` ambiguous form | use `[]` or explicit length |
| Modifying builtins | never |
| Default param `{}`/`[]` | OK in JS (new each call) — unlike Python |

## Anti-patterns

- `export default class Foo`
- `export let counter = 0` mutated externally
- `import *` + default export mixing without namespace plan
- ASI footguns (line starting with `[` or `(` after previous line)
- `if (items.length)` when `0` is valid data
- `new Boolean(false)` in conditions

## Skill trace

| Artifact | Role |
|---|---|
| `javascript-style-modules-exports.md` | import/export boundaries |
| `javascript-style-variables-equality.md` | const/let, ===, truthiness |
| `javascript-style-formatting-control.md` | braces, semicolons, commas |
| `javascript-style-functions-disallowed.md` | arrows, naming, banned features |
| `javascript-coding-practices` | application skill |
