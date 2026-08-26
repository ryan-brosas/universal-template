<!-- capsule-v2 -->
# Divide-and-subtract permission bitmask — how do you decode an integer column into view/add/edit/delete booleans?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How are role permissions stored and expanded, and what does `can()` check against?

## Roles_model::get_permissions_by_slug + can()/cannot()
**Path/Symbol:** `application/models/Roles_model.php:213` (`get_permissions_by_slug`, 213–253), `application/helpers/permission_helper.php:28` (`can`), `:68` (`cannot`).
**Signature:** `can(string $action, string $resource, ?int $user_id = null): bool`
**Data Shape:** Constants (`application/config/constants.php:62-65`): `PRIV_VIEW=1, PRIV_ADD=2, PRIV_EDIT=4, PRIV_DELETE=8`; resource columns per role row (`appointments`, `customers`, `services`, `users`, `system_settings`, `user_settings`, `webhooks`, `blocked_periods`); each column holds a summed bitmask.

### Decisive source
```php
// application/models/Roles_model.php:233-247 — descending divide-and-subtract for DELETE/EDIT/ADD; view unconditional
if ($value > 0) {
    if ((int) ($value / PRIV_DELETE) === 1) { $permissions[$resource]['delete'] = true; $value -= PRIV_DELETE; }
    if ((int) ($value / PRIV_EDIT)   === 1) { $permissions[$resource]['edit']   = true; $value -= PRIV_EDIT;   }
    if ((int) ($value / PRIV_ADD)    === 1) { $permissions[$resource]['add']    = true; }
    $permissions[$resource]['view'] = true;   // ANY nonzero value grants view
}
// seed rows (migrations/001_specific_calendar_sync.php:484+): admin = 15 on every resource;
// provider = appointments 15 / customers 15 / user_settings 15, rest 0; customer = all 0.
```

**Flow:** `can()` resolves role slug from session (or explicit user id → users→roles chain) → fetches the decoded map → returns `$permissions[$resource][$action] ?? false`. Controllers gate writes with `$required_permissions = !empty($appointment['id']) ? can('add', PRIV_APPOINTMENTS) : can('edit', PRIV_APPOINTMENTS)` (deliberate swap at `Calendar.php:315-317`: creating requires **add**, editing requires **edit**).
**Invariant:** decode MUST go highest-bit-first with subtraction; testing bits low-first misclassifies sums like 5 (=view+edit). VIEW is NOT bit-tested in the decoder — any nonzero column value implies view, so a value of 2 yields `{view:true, add:true}`. Unknown resources/actions fail CLOSED via `?? false`, and empty role slug fails closed. The add/edit swap on the save path is intentional — porters who "fix" it break edit-permission enforcement.
**Probe:** `bash -c 'grep -c "(\$value / PRIV_" application/models/Roles_model.php'` (= 3 division sites: delete/edit/add; view has none).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "get_permissions_by_slug", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the 1/2/4/8 constants + descending decode + fail-closed lookup; adapt storage to JSON if you must but keep highest-first semantics; omit the legacy `get_value/get_row` deprecated shims around it. Direct tests: none upstream.
