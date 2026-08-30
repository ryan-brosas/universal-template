<!-- capsule-v2 -->
# Functions and scope — are locals tight and control flow explicit?

**Source:** lua-users §Scope/Lua Idioms; LuaRocks §Function declaration/calls/Conditionals. **Question:** Are side effects bounded and calls unambiguous?

## Scope seam
**Path/Symbol:** functions and blocks in `.lua` files.
**Signature:** `local` declarations; `local function`; early return guards.
**Data Shape:** smallest lexical scope for each binding.

### Decisive pattern
```lua
local function load_user(id)
    if not id then
        return nil, "missing id"
    end

    local record = fetch_record(id)
    if not record then
        return nil, "not found"
    end

    return normalize(record)
end

local name = options.name or "default"
local line = io.read()
if line then
    handle(line)
end
```

**Flow:** always `local` for variables and prefer `local function name()` over `local name = function()` → assign at smallest scope (declare near use) → validate early and return → use `if x then` when only nil matters; be explicit when `false` differs → default with `x = x or val` only when false/nil equivalent → use `and`/`or` tersely but avoid broken `x and y or z` when `y` may be false → call with parentheses when precedence unclear; keep `func("literal")` explicit → method calls via `:` sugar with `self` → append with `t[#t+1] = v` for arrays.
**Invariant:** global assignment, late-wide-scope locals, or ambiguous string-literal call without parens fails review.
**Probe:** luacheck `glob`/`unused`; manual precedence review on omitted-paren calls.

## Safety seam
**Flow:** avoid debug library and deprecated APIs (`table.getn`, etc.) in production paths.
**Invariant:** debug hooks in library hot path fails review.
**Probe:** grep `require \"debug\"` / deprecated API usage.

## Verdict
Local-first functions, guard returns, explicit calls, Lua truth idioms. Learning note: `lua-style-learning-note.md`.
