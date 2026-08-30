---
name: elixir-coding-practices
description: "Use when authoring or reviewing Elixir — mix format, snake_case/CamelCase naming, module attribute order, pipelines, @moduledoc/@spec, Error exceptions, and mix test/credo in CI."
disable-model-invocation: true
---

# Elixir Coding Practices

Application skill for Elixir style learning (`awesome-guidelines` deep ingest). For OTP/supervision design, combine with stack foundations.

## Core Principle

Elixir quality is **formatter-mechanical + explicit modules** — ordered attributes, documented public API, purposeful pipelines.

## When to Use / NOT

- Elixir/Phoenix/Mix libraries and applications.
- Setting up `mix format`, Credo, Dialyzer, ExUnit in CI.

**NOT when:**

- Erlang `.erl` — use Erlang practices when ingested.
- HEEx/templates only — validate `.ex` context modules.

## Workflow

1. **Format & modules** — mix format, module order (`elixir-style-formatting-modules.md`).
2. **Naming** — snake/Camel, ?, Error (`elixir-style-naming-functions.md`).
3. **Expressions** — pipes, cond, defs (`elixir-style-expressions-pipelines.md`).
4. **Docs & types** — moduledoc, spec, errors (`elixir-style-docs-types-errors.md`).
5. **Verify** — `mix format`, `mix test`, Credo/Dialyzer per project.

## Red Flags

- Unformatted source
- camelCase functions or snake_case modules
- Single-step pipe
- `@moduledoc` after `use`
- Missing `@spec` on public API (when Dialyzer enabled)
- Exception not ending in `Error`
- Capitalized raise message with `.`
- `unless ... else`
- Repetitive module namespace (`Foo.Foo`)
- Needless macros

## Verification

- `mix format --check-formatted`
- `mix test`
- `mix credo` / `mix dialyzer` (project policy)
- ExDoc build for public packages
- Capsule checklist on new modules

## Skill Result Contract

```xml
<skill_result>
  <skill>elixir-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>ex diff, format/test/credo output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>spec drift, pipe abuse, doc gap, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/elixir-style-learning-note.md`
- `awesome-guidelines/references/elixir-style-formatting-modules.md`
- `awesome-guidelines/references/elixir-style-naming-functions.md`
- `awesome-guidelines/references/elixir-style-expressions-pipelines.md`
- `awesome-guidelines/references/elixir-style-docs-types-errors.md`
