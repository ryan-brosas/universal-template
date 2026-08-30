# Julia style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `julia-style-*.md` capsules, `julia-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [invenia/BlueStyle](https://github.com/invenia/BlueStyle) (primary) | 4-space indent; 92 cols; UpperCamelCase modules/types; snake_case methods; explicit `using`; exports at top; `_internal` prefix; long-form `return`; `;` before kwargs; general type annotations; docstrings on exports; JuliaFormatter `style = "blue"` |
| [JuliaFormatter BlueStyle](https://juliaeditorsupport.github.io/JuliaFormatter.jl/stable/blue_style/) (secondary) | mechanical enforcement via `.JuliaFormatter.toml` |

**Not duplicated here:** SciMLStyle variant — follow project formatter config when set. Full Performance Tips — use Julia manual for micro-opts.

## Mental model

BlueStyle Julia is **package-scale consistency + explicit APIs**:

1. **Mechanical** — JuliaFormatter BlueStyle; 4 spaces; ≤92 columns; no trailing ws.
2. **Modules** — one `using` per line alphabetically; explicit imports in packages; exports grouped at top; module file = module block only.
3. **Methods** — action names with types in signature; short one-line defs only when they fit; long-form always `return`; kwargs separated by `;`.
4. **Types** — prefer general param types (`AbstractArray`, `Integer`); concrete fields when layout matters; `_foo` for internal API.
5. **Docs & tests** — docstrings on exported functions; intent comments; root `@testset`; avoid `0.0` noise in `@test`.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Indent | 4 spaces, no tabs |
| Line length | 92 characters |
| Whitespace | no pad inside `()`; spaces around binary ops; no trailing ws |
| Arrays/calls | trailing comma in multiline expanded form |
| Functions | no blank line after `function` open or before `end` |
| Modules | top-level module file — body not extra-indented |

### Naming

| Entity | Convention |
|---|---|
| Modules/types | UpperCamelCase |
| Functions | snake_case (1–2 words) |
| Globals | avoid; if needed `const MY_CONST` |
| Internal | leading `_` on functions/types/constants |
| Method names | action in name, type in signature (`submit(bid::Bid)`) |

### Imports & exports

| Topic | Rule |
|---|---|
| Import | `using` over `import`; one package per line; alphabetical |
| Explicit | `using Foo: a, b, c` grouped modules/types/funcs |
| Export | public API exported at top of main module file |
| Includes | imports in parent file, not each include |

### Methods & calls

| Case | Rule |
|---|---|
| Short def | one line only if fits 92 cols |
| Long def | explicit `return`; even `return nothing` |
| Params | each on own line when >92 cols |
| Keyword call | `f(x; y=3)` semicolon before kwargs |
| Types | as general as reasonable in signatures |
| Ternary | single line; no chains |
| Loops | `for i in xs` not `=` or `∈` |

### Docs & tests

| Topic | Rule |
|---|---|
| Docstrings | required on exports; wrap at 92; Markdown |
| Comments | intent not obvious restatement; capitalized sentences |
| Tests | single root `@testset` in runtests.jl |
| Compare | `@test x == 0` not `0.0` decoration |
| Perf | minimize globals; `const` when needed; functions over script |

## Anti-patterns

- Tabs or trailing whitespace
- `using A, B` on one line
- Unqualified extension via `import` without package prefix
- `def`-style implicit return in long functions
- `f(x, y=3)` without semicolon
- Type names baked into function names (`submit_bid`)
- Over-concrete type params when `AbstractArray` suffices
- Mutable globals without `const`
- Undocumented exported functions
- Multiline ternary chains
- `for i = 1:10`
- Code outside module block in module files
- Padding inside `Int64( value )`

## Skill trace

| Artifact | Role |
|---|---|
| `julia-style-formatting-layout.md` | indent, 92 cols, whitespace, commas |
| `julia-style-modules-imports.md` | using, export, module files |
| `julia-style-functions-methods.md` | return, kwargs, types, naming |
| `julia-style-docs-tests.md` | docstrings, comments, testsets |
| `julia-coding-practices/SKILL.md` | JuliaFormatter/test/Documenter in CI |
