# D style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `d-style-*.md` capsules, `d-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [The D Style (dlang.org/dstyle.html)](https://dlang.org/dstyle.html) (primary) | 4-space indent; camelCase/PascalCase; module lowercase; alias `T = U`; left-justify decls; property functions; explicit return types; ddoc Params/Returns; unittest blocks; Phobos braces/imports/attributes |
| [D Language Reference — Properties](https://dlang.org/spec/property.html) (secondary) | `@property` getters/setters as fields; getter must not alter state |

**Not duplicated here:** Full dfmt configuration debates — use project formatter. Every Phobos-only edge case — capsules capture probes; see source for official stdlib submission rules.

## Mental model

D style is **readable C-family layout with D idioms**:

1. **Naming** — camelCase functions/vars; PascalCase types; lowercase modules; acronym case consistency; `_` suffix for keyword conflicts only.
2. **Layout** — spaces not tabs; 4 columns per level; Allman braces in official/Phobos code; 80 soft / 120 hard line limit.
3. **Declarations** — left-associate types (`int[] x`); `alias New = Old`; properties over getters/setters; avoid UFCS abuse on side-effect calls.
4. **Safety & docs** — explicit `@safe`/`@nogc`/`pure`/`nothrow` when inferable; public symbols documented in Ddoc; unittest per function path.
5. **Templates** — constraints aligned with declaration; expression `in`/`out`/`invariant` when single assert; no unittest inside templates.

## Decision tables

### Naming

| Entity | Convention |
|---|---|
| Modules/packages | lowercase `[a-z0-9_]` |
| Types | PascalCase (`FooAndBar`) |
| Functions/vars | camelCase (`doneProcessing`) |
| Constants/enums | camelCase members (`secondsPerMinute`, `Direction.fwd`) |
| Keyword clash | trailing `_` (`nothrow_`) |
| Acronyms | uniform case (`UTFException`, `asciiChar`) |
| Private | no leading `_` unless private (D visibility) |

### Formatting (Phobos / official)

| Topic | Rule |
|---|---|
| Indent | 4 spaces |
| Braces | own line for blocks |
| Lines | soft 80, hard 120 |
| Spaces | after `if`/`for`; around binary ops; not after unary |
| Imports | selective/local; sorted; `import std.range : zip` |

### API style

| Case | Rule |
|---|---|
| Aliases | `alias size_t = uint;` not C typedef order |
| Properties | nouns; prefer over get/set pairs |
| UFCS | range chains OK; not `"hello".writeln` for side effects |
| Operators | keep conventional meaning |
| Return type | explicit on public functions |
| Hungarian | type-prefix bad; purpose suffix OK |

### Documentation & tests

| Case | Rule |
|---|---|
| Public API | Ddoc with Params/Returns |
| Tests | `unittest` immediately after function |
| Coverage | every path at least once |
| Templates | unittest outside template |
| Attributes | alphabetical; match function semantics |

## Anti-patterns

- snake_case identifiers (except modules)
- C-style `int []x, y` declarations
- Meaningless aliases (`alias INT = int`)
- Operator overload with non-conventional semantics
- UFCS on side-effect calls (`writeln;`)
- Getter/setter pairs instead of `@property`
- Missing Ddoc on exported symbols
- Unittest blocks inside templates
- Lines >120 columns
- Global imports when selective import suffices

## Skill trace

| Artifact | Role |
|---|---|
| `d-style-formatting-layout.md` | indent, braces, lines, imports |
| `d-style-naming-types.md` | camelCase, modules, acronyms |
| `d-style-declarations-api.md` | alias, properties, UFCS, operators |
| `d-style-docs-testing.md` | ddoc, unittest, attributes |
| `d-coding-practices/SKILL.md` | dfmt/dscanner/dub test in CI |
