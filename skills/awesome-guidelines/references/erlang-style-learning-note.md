# Erlang style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `erlang-style-*.md` capsules, `erlang-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [inaka/erlang_guidelines](https://github.com/inaka/erlang_guidelines) (primary) | 2-space indent; 100 cols; snake_case modules/functions/atoms; CamelCase variables; types/records first; clause functions over case; no `if`; no `-import`/`-export_all`; OTP API encapsulation; `-spec`; opaque records; iolists; minimal macros |
| [OTP Secure Coding Guidelines](https://www.erlang.org/doc/system/secure_coding.html) (secondary) | STL-001 restrictive matching; STL-002 avoid boolean blindness; DSG-002 `{ok,Result}` over exceptions; DSG-003 atom abuse; DSG-011 trusted deserialize; LNG-002 no legacy `catch`; explicit conversions over `binary_to_atom` |

**Not duplicated here:** Full OTP supervision design — use stack foundations. Every Elvis rule — enable project-relevant checks.

## Mental model

Erlang style is **pattern-first clarity + crash-visible bugs**:

1. **Layout** — 2 spaces, ≤100 columns, types/records at module top, exported functions grouped first.
2. **Naming** — `module_name`, `function_name`, `atom_name` (snake); `VariableName` (CamelCase); `#mod_state{}` + `-type state()`.
3. **Control flow** — pattern-match in function heads, not giant `case`; avoid `if`, legacy `catch`, deep nesting; `try … of … catch` not `case catch`.
4. **Modules & OTP** — explicit exports, no `-import`; encapsulate `gen_server` calls; tagged messages; `-spec` on public API.
5. **Safety** — restrictive matches; `{ok, _}` / `{error, _}`; no dynamic atoms from untrusted input; no `binary_to_term/1` on untrusted data.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Indent | spaces, 2 per level |
| Line length | ≤100 characters |
| Whitespace | spaces around operators/commas; no trailing ws |
| Types | at beginning of module |
| Records | before function bodies; field types defined |
| Functions | exported group first; prefer clause functions over top-level `case` |
| Headers | `.hrl` for macros only — no types/records/functions |

### Naming

| Entity | Convention |
|---|---|
| Modules | single convention (`foo_bar`) |
| Functions | lowercase snake_case |
| Variables | CamelCase, no underscores |
| Atoms/records | lowercase snake_case |
| State (OTP) | `#mod_state{}`, `-type state() :: #mod_state{}` |
| Macros | `ALL_UPPER_CASE`; avoid except literals/`?MODULE` |
| Messages | atom or `{tag, …}` tuple with tag in element 1 |

### Control flow

| Case | Rule |
|---|---|
| Branching | function clauses / `case` — not `if` |
| Large case | split into named functions |
| Nesting | ≤3 levels |
| Errors | `try … of … catch` — not `case catch` or legacy `catch` |
| Non-local return | avoid `throw`/`catch` for control flow |
| Booleans as args | avoid — use atoms (`enabled`/`disabled`) |
| Lists | iolists over string concat; folds/LCs over manual recursion when clearer |

### Modules & types

| Topic | Rule |
|---|---|
| Export | explicit `-export`; never `-compile(export_all)` |
| Import | don't `-import` |
| Records | module-local; opaque `-opaque` + accessors |
| Specs | `-spec` on exported functions; types in specs not raw records |
| Callbacks | `-callback` not `behaviour_info/1` |
| OTP | API functions wrap `gen_server:call/cast` in same module |

### Secure / restrictive (OTP)

| Case | Rule |
|---|---|
| Match | no catch-all when set is known; match `[]` not `_` for lists |
| Return check | `ok = file:write(...)` not `_ = …` |
| API errors | `{ok, Result} \| {error, Reason}` — user decides exception |
| Atoms | explicit mapping or `binary_to_existing_atom`; never blind `binary_to_atom` on input |
| Deserialize | trusted data only; `binary_to_term(B, [safe])`; no `file:consult/1` on untrusted |
| Dynamic calls | avoid when xref must see call graph |

## Anti-patterns

- `-compile(export_all)` or `-import`
- camelCase functions or snake_case variables
- Shared record definitions in `.hrl`
- Raw `gen_server:call` across module boundaries
- Top-level giant `case` instead of clause functions
- `if` expressions
- `case catch` or legacy `catch`
- Boolean function parameters
- Macros for module/function names
- `io:format` debug left in `src/`
- `binary_to_atom/1` on external input
- Catch-all `_` clauses hiding new return values
- Records in `-spec` instead of exported types
- God modules (500+ unrelated exports)

## Skill trace

| Artifact | Role |
|---|---|
| `erlang-style-formatting-modules.md` | indent, layout, types/records placement |
| `erlang-style-naming-types.md` | names, specs, opaque records, state |
| `erlang-style-control-flow.md` | clauses, case/if/catch, nesting |
| `erlang-style-otp-security.md` | exports, OTP API, restrictive/safe coding |
| `erlang-coding-practices/SKILL.md` | Elvis/dialyzer/xref/rebar3 test in CI |
