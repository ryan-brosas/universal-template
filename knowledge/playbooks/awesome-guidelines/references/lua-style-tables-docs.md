<!-- capsule-v2 -->
# Tables and docs — are data literals clear and public API documented?

**Source:** LuaRocks §Tables/Functions in tables/Documentation; lua-users §Commenting. **Question:** Can readers see record shape and module contract without reading bodies?

## Table seam
**Path/Symbol:** table literals and module method tables.
**Signature:** trailing comma; dot vs bracket access; external module functions.
**Data Shape:** LDoc headers on exported functions.

### Decisive pattern
```lua
--- Load manifest for a repository URL.
-- @param repo_url string repository location
-- @return table|nil manifest or nil, err, code
function manif.load_manifest(repo_url)
    -- code
end

local player = {
    name = "Jack",
    class = "Rogue",
}

local vehicles = load_vehicles()
if vehicles.Porsche then
    handle(vehicles.Porsche)
end

local version_mt = {
    __eq = function(a, b)
        return a.major == b.major
    end,
}
```

**Flow:** build tables in one literal when possible with trailing comma → use `key = value` syntax; `["UTF-8"]` only when identifier-invalid → access known fields with dot; dynamic keys with `[]` → for modules declare methods as `function M.fn()` outside small metatables; keep metamethods inside metatable literal → document exports with LDoc (`---` blocks, `@param`/`@return`) → prefer LDoc over inline how-comments; use TODO/FIXME tags → run luacheck in CI on changed files.
**Invariant:** mixed key styles in one literal, undocumented exported function, or subscript on known static field fails review.
**Probe:** luacheck; LDoc generation; exported function doc grep.

## String seam
**Flow:** double quotes for strings; single quotes when string contains `"`.
**Invariant:** inconsistent quote style in same module fails minor review.
**Probe:** string delimiter spot check.

## Verdict
Trailing-comma tables, dot/bracket discipline, LDoc exports, luacheck. Learning note: `lua-style-learning-note.md`.
