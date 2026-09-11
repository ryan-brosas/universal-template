---
title: erlang-coding-practices
summary: Use when authoring or reviewing Erlang, 2-space layout, snake_case/CamelCase naming, clause functions, -spec exports, OTP API encapsulation, {ok,error} returns, atom/deserialize safety, and Elvis/dialyzer/xref in CI.
kind: playbook
---

# Erlang Coding Practices

Application skill for Erlang style. For supervision trees and release tooling, consult OTP's own source or docs.

## Core Principle

Erlang quality is **pattern-visible modules + crash-loud bugs**, explicit exports, clause-driven control flow, and restrictive matching on every boundary.

## When to Use / NOT

- Erlang/OTP applications, libraries, and `src/*.erl` modules.
- Setting up Elvis, Dialyzer, xref, rebar3 test/dialyzer in CI.

**NOT when:**

- Elixir code, use `elixir-coding-practices` (BEAM overlap on security only).
- Generated `.app` / protobuf stubs, validate generators.

## Workflow

1. **Layout**, indent, types/records, grouping.
2. **Names & types**, snake/CamelCase, specs, opaque state.
3. **Control flow**, clauses, try/catch, no if.
4. **OTP & security**, exports, API wrap, input safety.
5. **Verify**, Elvis, Dialyzer, xref, rebar3 test on changed modules.

## Red Flags

- `-compile(export_all)` or `-import`
- camelCase functions or snake_case variables
- Records/types in `.hrl`
- Cross-module raw `gen_server:call`
- Giant top-level `case` or `if`
- `case catch` / legacy `catch` / control-flow `throw`
- Boolean function parameters
- `binary_to_atom/1` on external input
- `binary_to_term/1` without `[safe]` on untrusted data
- Catch-all `_` when return set is known
- `_ =` on fallible standard-library calls
- Debug `io:format` in `src/`
- God modules or macros for module names

## Verification

- `rebar3 dialyzer` / project Dialyzer profile
- Elvis (Inaka rules or project config)
- `xref` / cross-reference check where configured
- `rebar3 eunit` or Common Test on changed modules
