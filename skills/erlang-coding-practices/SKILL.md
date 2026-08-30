---
name: erlang-coding-practices
description: "Use when authoring or reviewing Erlang — 2-space layout, snake_case/CamelCase naming, clause functions, -spec exports, OTP API encapsulation, {ok,error} returns, atom/deserialize safety, and Elvis/dialyzer/xref in CI."
disable-model-invocation: true
---

# Erlang Coding Practices

Application skill for Erlang style learning (`awesome-guidelines` deep ingest). For supervision trees and release tooling, combine with OTP stack foundations.

## Core Principle

Erlang quality is **pattern-visible modules + crash-loud bugs** — explicit exports, clause-driven control flow, and restrictive matching on every boundary.

## When to Use / NOT

- Erlang/OTP applications, libraries, and `src/*.erl` modules.
- Setting up Elvis, Dialyzer, xref, rebar3 test/dialyzer in CI.

**NOT when:**

- Elixir code — use `elixir-coding-practices` (BEAM overlap on security only).
- Generated `.app` / protobuf stubs — validate generators.

## Workflow

1. **Layout** — indent, types/records, grouping (`erlang-style-formatting-modules.md`).
2. **Names & types** — snake/CamelCase, specs, opaque state (`erlang-style-naming-types.md`).
3. **Control flow** — clauses, try/catch, no if (`erlang-style-control-flow.md`).
4. **OTP & security** — exports, API wrap, input safety (`erlang-style-otp-security.md`).
5. **Verify** — Elvis, Dialyzer, xref, rebar3 test on changed modules.

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
- Capsule checklist on exported `-spec` list

## Skill Result Contract

```xml
<skill_result>
  <skill>erlang-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>erl diff, Elvis/dialyzer/xref/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>atom exhaustion, silent match failure, OTP coupling, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/erlang-style-learning-note.md`
- `awesome-guidelines/references/erlang-style-formatting-modules.md`
- `awesome-guidelines/references/erlang-style-naming-types.md`
- `awesome-guidelines/references/erlang-style-control-flow.md`
- `awesome-guidelines/references/erlang-style-otp-security.md`
