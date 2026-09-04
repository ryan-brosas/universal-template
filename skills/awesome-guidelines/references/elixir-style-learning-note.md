# Elixir style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `elixir-style-*.md` capsules, `elixir-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [christopheradams/elixir_style_guide](https://github.com/christopheradams/elixir_style_guide) (primary) | `mix format`; 98-char lines; snake_case/CamelCase; pipe operator; module attribute order; `@moduledoc` first; `@spec` + `@type t`; `Error` suffix; keyword list syntax; ExUnit assert order |
| [Elixir naming conventions](https://hexdocs.pm/elixir/naming-conventions.html) (secondary) | official snake_case atoms/functions; CamelCase modules; `?` predicates; `is_` guard-safe names |

**Not duplicated here:** Every Credo rule — enable project-relevant checks. Full OTP/supervision patterns — use stack capsules in `skills/*-foundation`.

## Mental model

Elixir style is **formatter-first + community conventions**:

1. **Mechanical** — `mix format` / `.formatter.exs`; 98 columns; spaces around operators.
2. **Naming** — `SomeModule` / `some_function` / `cool?` / `is_ok/1` guards; `snake_case` files mirror modules.
3. **Modules** — one module per file; nested dirs; ordered `@moduledoc`, `use`, `import`, `alias`, `@type`, `def`.
4. **Expressions** — pipelines with bare first arg; no single-step pipe; `if` not `unless else`; `true` in `cond`.
5. **Contracts** — `@moduledoc`, `@doc`, `@spec`, `@type t`; exceptions end with `Error`; lowercase raise messages.

## Decision tables

### Formatting

| Topic | Rule |
|---|---|
| Format | `mix format` mandatory |
| Line length | 98 chars (formatter default) |
| Whitespace | spaces around ops; no trailing ws |
| `def` | parens when args; no parens when zero arity |
| Module file | `my_module.ex` → `MyModule` |

### Naming

| Entity | Convention |
|---|---|
| Modules | CamelCase (`SomeXML`) |
| Functions/vars/atoms | snake_case |
| Predicates | trailing `?` |
| Guard macros | `is_` prefix (`defguard`) |
| Exceptions | `*Error` module name |
| Main struct type | `@type t` |

### Modules

| Order | Directive |
|---|---|
| 1 | `@moduledoc` |
| 2 | `@behaviour` |
| 3 | `use` |
| 4 | `import` / `require` |
| 5 | `alias` (alphabetical) |
| 6 | `@type`, `@callback` |
| 7 | `def` / `defp` |

### Expressions & tests

| Case | Rule |
|---|---|
| Pipe | multi-step only; data leftmost |
| unless | no `else` — use `if` |
| cond | last clause `true` |
| Keyword lists | `[a: 1, b: 2]` syntax |
| assert | `assert actual == expected` |
| Metaprogramming | avoid needless macros |

## Anti-patterns

- Skipping `mix format`
- camelCase functions or snake_case modules
- Single-step pipe (`x |> f()`)
- `@moduledoc` after `use`
- Missing `@spec` on public API (Dialyzer teams)
- Exception not ending in `Error`
- Capitalized raise messages with trailing `.`
- `unless ... else`
- Repetitive module names (`Todo.Todo`)
- Private/public function name collision pattern `def foo` / `defp do_foo`

## Skill trace

| Artifact | Role |
|---|---|
| `elixir-style-formatting-modules.md` | format, files, module order |
| `elixir-style-naming-functions.md` | snake/Camel, ?, is_, Error |
| `elixir-style-expressions-pipelines.md` | pipe, def, cond, unless |
| `elixir-style-docs-types-errors.md` | moduledoc, spec, raise, tests |
| `elixir-coding-practices/SKILL.md` | mix format/credo/dialyzer/test in CI |
