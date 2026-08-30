---
name: lua-coding-practices
description: "Use when authoring or reviewing Lua — local-first modules, 2–4 space layout, snake_case/CamelCase naming, return-M pattern, guard returns, table/LDoc idioms, and luacheck/LDoc in CI."
disable-model-invocation: true
---

# Lua Coding Practices

Application skill for Lua style learning (`awesome-guidelines` deep ingest). For Luau/Roblox or OpenResty-specific rules, follow stack foundations first.

## Core Principle

Lua quality is **local scope + explicit modules** — return a table, require into locals, document the exported surface.

## When to Use / NOT

- Lua 5.x libraries, Neovim/Redis/OpenResty scripts, embedded game logic (non-Luau).
- Setting up luacheck, LDoc, busted/luaunit in CI.

**NOT when:**

- Luau-typed Roblox code — use project Luau guide.
- Generated `.lua` stubs — validate generators.

## Workflow

1. **Layout** — indent, spacing, blocks (`lua-style-formatting-layout.md`).
2. **Modules** — names, return M (`lua-style-naming-modules.md`).
3. **Functions** — local, guards, calls (`lua-style-functions-scope.md`).
4. **Tables/docs** — literals, LDoc (`lua-style-tables-docs.md`).
5. **Verify** — luacheck, LDoc (if applicable), tests on changed modules.

## Red Flags

- Globals without explicit `_G` discipline
- `module(..., package.seeall)`
- Missing `local` on bindings
- Semicolons as statement separators
- `local x = function()` instead of `local function`
- Ambiguous omitted-paren string calls
- Broken `x and y or z` when y may be false
- debug library in production paths
- Deprecated 5.0 APIs
- Undocumented exported functions
- dot vs `[]` misuse on static keys
- No trailing comma in multiline tables
- Deep nesting without `end` comments
- `table.insert` for simple append only

## Verification

- `luacheck .` (project `.luacheckrc`)
- LDoc build for documented modules
- busted/luaunit test run (project harness)
- Capsule checklist on `return M` module pattern

## Skill Result Contract

```xml
<skill_result>
  <skill>lua-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>lua diff, luacheck/LDoc/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>global leak, module pollution, precedence bug, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/lua-style-learning-note.md`
- `awesome-guidelines/references/lua-style-formatting-layout.md`
- `awesome-guidelines/references/lua-style-naming-modules.md`
- `awesome-guidelines/references/lua-style-functions-scope.md`
- `awesome-guidelines/references/lua-style-tables-docs.md`
