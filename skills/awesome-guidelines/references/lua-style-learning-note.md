# Lua style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `lua-style-*.md` capsules, `lua-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [lua-users wiki LuaStyleGuide](http://lua-users.org/wiki/LuaStyleGuide) (primary) | 2-space indent; snake_case/lowercase; `is_` booleans; `local` over global; `return M` modules not `module()`; end terminators; truthiness idioms; avoid debug/deprecated APIs |
| [LuaRocks lua-style-guide](https://github.com/luarocks/lua-style-guide) (secondary) | always `local`; snake_case; CamelCase classes; LDoc; early return; named `local function`; parens on calls; dot vs `[]`; table trailing commas; no semicolons; luacheck |

**Not duplicated here:** Roblox Luau-specific typing — use stack capsules in `foundation-pack/`. Full Olivine-Labs guide — overlaps wiki/LuaRocks.

## Mental model

Lua style is **local-first modules with readable nesting**:

1. **Layout** — 2–4 space indent (pick one per project; wiki/PiL use 2); spaces around operators; no semicolons; `--` comment space.
2. **Naming** — descriptive by scope; snake_case functions; CamelCase classes; `is_` predicates; ALL_CAPS sparingly for constants.
3. **Scope & modules** — `local` always; smallest scope; `local M = {}` + `return M`; no `module(..., package.seeall)`.
4. **Functions** — prefer `local function`; early validation/return; explicit parens when precedence unclear; `:` for methods.
5. **Tables & docs** — literal tables with trailing comma; dot for known keys; LDoc on public API; luacheck in CI.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Indent | 2–4 spaces; no tabs; one project-wide choice |
| Lines | split complex expressions; one statement per line |
| Semicolons | avoid |
| Comments | space after `--`; end `-- if/for` on long blocks |
| Spacing | space after `,`; around binary operators |

### Naming

| Entity | Convention |
|---|---|
| Locals/functions | snake_case (or short in tiny scope) |
| Classes/metatables | CamelCase (`BankAccount`) |
| Objects | lower camel or snake per project |
| Booleans | `is_directory`, `is_loaded` |
| Constants | ALL_CAPS sparingly |
| Ignored | `_` in loops |
| Modules | short lowercase (`luasql.postgres`) |
| Reserved | no `_UPPER` globals (Lua internal pattern) |

### Scope & modules

| Topic | Rule |
|---|---|
| Variables | `local` by default |
| Globals | avoid; use `_G` prefix only if exceptional |
| Module | `local M = {}; …; return M` |
| Require | `local MT = require "pkg.mod"` |
| Class module | callable metatable + `self` methods |
| Deprecated | avoid `table.getn`, `module()`, etc. |

### Functions & control

| Case | Rule |
|---|---|
| Declaration | `local function foo()` over `local foo = function()` |
| Validation | guard clauses early |
| Calls | parens when precedence ambiguous |
| Methods | `obj:method()` sugar |
| Conditionals | `if x then` when nil/false differ not needed |
| Default | `x = x or default` (mind false) |
| Append | `t[#t+1] = v` for arrays |

### Tables & API

| Case | Rule |
|---|---|
| Literals | populate at once; trailing comma |
| Keys | `key = val`; `["UTF-8"]` when needed |
| Access | `.field` for known; `[var]` dynamic |
| Module fns | `function M.fn()` outside table for large modules |
| Metatable | fns inside table literal |
| Docs | LDoc on exported functions |

## Anti-patterns

- Global variables without `_G` discipline
- `module(..., package.seeall)`
- Missing `local` on declarations
- Semicolon statement chains
- `table.insert` for simple append
- Bare `head`/`fromJust` without guard
- debug library in trusted/production paths
- Deprecated 5.0 APIs in 5.x code
- Hungarian notation overload on obvious types
- Omitting parens on ambiguous string-literal calls
- `x and y or z` when `y` may be false/nil
- Mixed table key syntax in one literal
- Undocumented public module functions

## Skill trace

| Artifact | Role |
|---|---|
| `lua-style-formatting-layout.md` | indent, spacing, blocks, end comments |
| `lua-style-naming-modules.md` | names, module return pattern |
| `lua-style-functions-scope.md` | local, early return, calls, idioms |
| `lua-style-tables-docs.md` | literals, dot/bracket, LDoc, luacheck |
| `lua-coding-practices/SKILL.md` | luacheck/LDoc/test in CI |
