<!-- capsule-v2 -->
# Naming and modules — are globals avoided and APIs namespaced?

**Source:** lua-users §Naming/Modules; LuaRocks §Variable names. **Question:** Does each file return a module table without polluting `_G`?

## Module seam
**Path/Symbol:** library `.lua` files and require graph.
**Signature:** `local M = {}; return M`; snake_case API; CamelCase classes.
**Data Shape:** `local Mod = require "pkg.mod"`.

### Decisive pattern
```lua
-- finance/BankAccount.lua
local M = {}
M.__index = M

setmetatable(M, {
    __call = function()
        return setmetatable({ balance = 0 }, M)
    end,
})

function M:add(value)
    self.balance = self.balance + value
end

return M
```

```lua
local BankAccount = require "finance.BankAccount"
local account = BankAccount()
account:add(10)
```

**Flow:** never `module(..., package.seeall)` → build `local M = {}`, define API on `M`, `return M` → require into local (`local MT = require "hello.mytest"`) → module names short lowercase (`luasql.postgres`) → functions snake_case; classes CamelCase; predicates `is_*` → constants ALL_CAPS sparingly → `_` for ignored loop vars; descriptive names for wide scope, short only in tiny loops.
**Invariant:** global assignment without `_G` prefix, seeall modules, or `_VERSION`-style custom globals fails review.
**Probe:** grep `^[^l].*= require` missing local; `module(` usage; undeclared global luacheck warnings.

## Naming seam
**Flow:** avoid Hungarian noise on obvious types; don't use `_UPPER` names (Lua reserved pattern).
**Invariant:** `GetValue` camelCase methods in non-OOP Lua libraries fails consistency review.
**Probe:** naming convention audit on exported functions.

## Verdict
return-M modules, local requires, snake_case + CamelCase classes. Learning note: `lua-style-learning-note.md`.
