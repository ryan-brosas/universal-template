# Node.js platform style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `node-style-*.md` capsules, `node-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [felixge/node-style-guide](https://github.com/felixge/node-style-guide) (primary) | 2-space indent; semicolons; 80 cols; single quotes; K&R braces; one var per statement; camelCase; === ; early return; named closures; requires at top; no prototype extension |
| [microsoft/nodejs-guidelines](https://github.com/microsoft/nodejs-guidelines) (primary platform) | npm/package.json; PORT env; node_modules gitignore; Windows MAX_PATH; native addons; cross-platform modules; local vs global npm |
| `javascript-coding-practices` (secondary modernizer) | Prefer `const`/`let` over felixge `var`; named ES exports — apply when not locked to legacy felixge/JSHint profile |
| `mdn-code-examples-practices` (secondary) | MDN JS example rules overlap (===, braces) — Node app code vs doc examples |

**Scope:** **Node.js** application/module JavaScript (CommonJS and modern ESM). **Browser-only JS:** `javascript-coding-practices`. **TypeScript Node:** add `typescript-coding-standards`.

**Modernization note:** felixge predates widespread `const`/`let` and recommends `var` + UPPERCASE `var` constants. New Node code should use `const`/`let` and `const` for constants per `javascript-coding-practices` unless project explicitly follows felixge `.jshintrc` verbatim.

## Mental model

Node quality is **small readable modules** plus **platform-safe packaging**:

1. **Formatting** — 2 spaces; semicolons; 80 columns; single quotes; same-line braces; no trailing WS.
2. **Functions/modules** — short functions; return early; named callbacks; requires at top; no nested closures; no `Array.prototype` hacks.
3. **Conditionals/naming** — strict `===`; descriptive predicate vars; lowerCamelCase; UpperCamelCase classes.
4. **Platform/npm** — `package.json` deps; `process.env.PORT`; ignore `node_modules`; short paths on Windows; cross-platform by default; pin versions.

## Decision tables

### Formatting (felixge)

| Topic | Rule |
|---|---|
| Indent | 2 spaces; never mix tabs and spaces |
| Newlines | LF `\n`; newline at EOF |
| Trailing WS | none |
| Semicolons | always |
| Line length | 80 characters |
| Quotes | single quotes (double for JSON) |
| Braces | opening `{` same line as statement |
| var declarations | one variable per `var` statement |
| EditorConfig | use repo `.editorconfig` when present |

### Naming & variables

| Topic | Rule |
|---|---|
| Variables/functions | lowerCamelCase |
| Classes | UpperCamelCase |
| Constants | UPPERCASE (felixge `var`); prefer `const` UPPERCASE modern |
| Objects/arrays | trailing commas OK; short literals one line |
| Keys | quote only when interpreter requires |

### Conditionals & functions

| Topic | Rule |
|---|---|
| Equality | `===` / `!==` |
| Ternary | multi-line when used |
| Conditions | assign complex tests to named booleans |
| Function size | ~15 lines target |
| Control flow | return early; avoid deep nesting |
| Closures | name callbacks; avoid nesting — extract named function |
| Chaining | one method per line; indent chain |
| Comments | `//` for non-trivial intent; not restating code |

### Module hygiene (felixge + Microsoft)

| Topic | Rule |
|---|---|
| require/import | at top of file — dependencies visible |
| Built-ins | never extend native prototypes |
| eval/with/freeze tricks | avoid |
| Setters | avoid; getters OK without side effects |
| package.json | track deps; `--save` / `--save-dev` appropriately |
| node_modules | gitignore; restore with `npm install` |
| PORT | `process.env.PORT \|\| default` |
| Global npm | prefer local + npm scripts over `-g` when possible |
| Windows paths | short base path (e.g. `C:\src`); npm dedupe; npm 3+ flat tree |
| Native addons | identify `node-gyp`/`nan`; document build prerequisites |
| Cross-platform | modules should run on Windows/Linux/macOS unless private |

## Anti-patterns

- Tabs or mixed tab/space indent
- Trailing whitespace
- Double quotes for non-JSON strings (felixge profile)
- Brace on next line (Allman) in felixge style
- Multi-var comma `var a=1, b=2`
- snake_case identifiers
- Loose `==` / `!=`
- Inline complex `if` conditions without named predicate
- Deeply nested if/else (no early return)
- Anonymous nested callbacks
- Extending `Array.prototype` / native prototypes
- Setters with side effects
- `eval`, `with`
- requires scattered mid-file
- Committing `node_modules` to git
- `"*"` wild dependency versions in production
- Long Windows paths without MAX_PATH mitigation
- Windows-only public npm module without guard
- Global `-g` install causing version clashes across projects

## Skill trace

| Artifact | Role |
|---|---|
| `node-style-formatting-layout.md` | indent, semicolons, quotes, braces |
| `node-style-functions-modules.md` | size, closures, requires, prototypes |
| `node-style-conditionals-naming.md` | ===, naming, literals |
| `node-style-platform-verify.md` | npm, Windows, native, cross-platform |
| `node-coding-practices/SKILL.md` | Node patch/review workflow |

## Relation to sibling skills

| felixge/Microsft Node | javascript-coding-practices |
|---|---|
| var + one var per line | const/let; one per line still good |
| single quotes | project may use Prettier double — pick one |
| semicolons + 2 space | aligned |
| CommonJS require top | ESM import top |
| Platform/npm (Microsoft) | not in generic JS skill |
