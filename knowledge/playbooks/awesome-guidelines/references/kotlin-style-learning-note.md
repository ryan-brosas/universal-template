# Kotlin style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `kotlin-style-*.md` capsules, `kotlin-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Kotlin Coding Conventions](https://kotlinlang.org/docs/coding-conventions.html) (primary) | 4-space indent; K&R braces; package/file layout; class member order; naming (PascalCase/camelCase/SCREAMING_SNAKE); modifier order; trailing commas at declarations; `val` immutability; default params over overloads; expression `if`/`when`; backing properties `_foo` |
| [Google Android Kotlin Style Guide](https://developer.android.com/kotlin/style-guide) (secondary) | no wildcard imports; logical import order; expression-form conditionals; acronym casing alignment |

**Not duplicated here:** Compose `@Composable` naming, multiplatform file suffixes in full — see official guide when KMP/Android stack is known. Scope-function choice — link to Kotlin docs, capsule gives probe only.

## Mental model

Kotlin style in this catalog is **official Kotlin mechanical format plus immutability-first idioms**:

1. **Layout** — 4 spaces, opening brace on same line, no horizontal alignment games, trailing commas on declarations.
2. **Organization** — pure Kotlin omits common root package in paths; one primary type per file when possible; class body order: properties → secondary ctors → methods → companion.
3. **Naming** — lowercase packages; PascalCase types; camelCase members; `const`/deeply immutable `SCREAMING_SNAKE`; factory functions may match type name (`fun Foo(): Foo`).
4. **Idioms** — prefer `val` and immutable collection interfaces; default parameters over overloads; expression `if`/`when`; named args when primitives/`Boolean` ambiguous; libraries expose explicit visibility and return types.

## Decision tables

### Formatting

| Topic | Rule |
|---|---|
| Indent | 4 spaces, no tabs |
| Braces | opening `{` end of line; closing aligned with opener |
| Whitespace | spaces around binary ops; no space before call `(`; no space around `.`/`?.` |
| Modifiers | fixed order: visibility → expect/actual → open/final/… → override → … |
| Annotations | before modifiers; file annotations before `package` |
| Trailing comma | encouraged at declaration sites |
| Semicolons | omit |

### Files & packages

| Topic | Rule |
|---|---|
| Package | lowercase, no underscores (`org.example.project`) |
| Single-type file | `InvoiceService.kt` matches class name |
| Multi-decl file | descriptive PascalCase name, no `Util` |
| Pure Kotlin tree | drop common root package segment in directories |
| Imports | no wildcard (Android); explicit aliases for clashes |

### Naming

| Element | Convention |
|---|---|
| Class/object | PascalCase (`HttpInputStream`) |
| Function/property | camelCase |
| Constant | SCREAMING_SNAKE for `const` / deeply immutable |
| Backing property | `_elements` private, `elements` public getter |
| Acronyms | 2-letter all caps (`IOStream`); longer capitalize first only (`XmlParser`) |

### Class layout

| Order | Members |
|---|---|
| 1 | properties + init blocks |
| 2 | secondary constructors |
| 3 | methods (related grouped, overloads adjacent) |
| 4 | companion object |
| Nested | near use site, or end if external-only |

### Idioms

| Case | Rule |
|---|---|
| Mutability | `val` + `List`/`Set`/`Map` interfaces; `listOf()` not `arrayListOf()` when immutable |
| Overloads | prefer default parameter values |
| Binary branch | `if` not `when` |
| Multi-arg clarity | named arguments |
| Library API | explicit visibility + return types + KDoc on public members |

## Anti-patterns

- Tabs or 2-space indent in shared Kotlin
- `import foo.*`
- `var` when value never reassigned
- `HashSet`/`ArrayList` in public API parameters when immutable suffices
- Overload trio instead of default parameters
- Alphabetical method sorting separating related logic
- `StringUtil.kt` meaningless file names
- Library public API without explicit return types

## Skill trace

| Artifact | Role |
|---|---|
| `kotlin-style-formatting-layout.md` | indent, braces, modifiers, commas |
| `kotlin-style-naming-files.md` | packages, files, constants, backing props |
| `kotlin-style-organization-classes.md` | directories, class layout, extensions |
| `kotlin-style-idioms-api.md` | val/immutable, defaults, if/when, library API |
| `kotlin-coding-practices/SKILL.md` | ktlint/detekt/IDE formatter in CI |
