---
title: elixir-coding-practices
summary: Use when authoring or reviewing Elixir, mix format, snake_case/CamelCase naming, module attribute order, pipelines, @moduledoc/@spec, Error exceptions, and mix test/credo in CI.
kind: playbook
---

# Elixir Coding Practices

Application skill for Elixir style. For OTP/supervision design, combine with the framework's own source or docs.

## Core Principle

Elixir quality is **formatter-mechanical + explicit modules**, ordered attributes, documented public API, purposeful pipelines.

## When to Use / NOT

- Elixir/Phoenix/Mix libraries and applications.
- Setting up `mix format`, Credo, Dialyzer, ExUnit in CI.

**NOT when:**

- Erlang `.erl`, use Erlang practices.
- HEEx/templates only, validate `.ex` context modules.

## Workflow

1. **Format & modules**, mix format, module order.
2. **Naming**, snake/Camel,?, Error.
3. **Expressions**, pipes, cond, defs.
4. **Docs & types**, moduledoc, spec, errors.
5. **Verify**, `mix format`, `mix test`, Credo/Dialyzer per project.

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
