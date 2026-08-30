<!-- capsule-v2 -->
# Tenant-FK write guards — how do create/update actions reject cross-tenant references and partial custom-field patches without trusting the client?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When a write action accepts arrays of related-record ids and partial custom-field maps from the client, what stands between the payload and another tenant's rows — and how do partial updates avoid wiping untouched fields?

## Count-based FK validation + merge-before-save custom fields
**Path/Symbol:** `app/Support/TenantFkValidator.php` (whole, 156L: `assertOwned`, `assertOwnedMany`, `assertUsersInWorkspace`, `assertUserInWorkspace`); `app/Support/CustomFieldMerger.php` (whole, 67L, `merge(Model $model, array $attributes): array`); consumed by `app/Actions/Task/CreateTask.php` (86L) and `app/Actions/Task/UpdateTask.php` (91L).
**Signature:** `assertOwnedMany(User $user, array $data, array $fkArrayToModelMap): void` — per field: skip non-array/empty, `array_unique` + `strval` the input, then `count($modelClass::query()->where('team_id', $teamId)->whereIn(key, $unique)) === count($unique)` or throw `ValidationException` keyed by field. `assertUsersInWorkspace` builds the member set as `team->users()->pluck('users.id')` PLUS `team->user_id` (the owner may not be a pivot row) and does strict string `in_array` per value.
**Data Shape:** all four validators throw `ValidationException::withMessages([$field => ...])` (field-keyed, form-renderable) and refuse with `'No active workspace.'` when `current_team_id` is null. The action shape: policy gate (`abort_unless($user->can(...))`) → FK validation → `Arr::pull`/`Arr::only` shaping → one `DB::transaction` (create + `sync()` each relation) → notify AFTER commit → return eager-loaded (`customFieldValues.customField.options`).

### Decisive source
```php
$unique = array_values(array_unique(array_map(strval(...), $values)));

$owned = $modelClass::query()
    ->where('team_id', $teamId)
    ->whereIn((new $modelClass)->getKeyName(), $unique)
    ->count();

if ($owned !== count($unique)) {
    throw ValidationException::withMessages([
        $field => "One or more {$field} are not in your workspace.",
    ]);
}
```

```php
// CustomFieldMerger docblock: the custom-fields package's saveCustomFields()
// iterates ALL defined fields and writes null for any not present in the
// submitted array. This helper loads the model's current values and merges
// submitted fields on top, so omitted fields are preserved.
$attributes['custom_fields'] = array_merge($existing, $attributes['custom_fields']);
```

**Flow:** `UpdateTask` captures `$previousAssigneeIds` BEFORE the transaction (input to the diff-based fan-out), validates FKs, runs `CustomFieldMerger::merge` so a partial `custom_fields` map is merged over current values (orphaned value rows — whose field was deleted — are filtered via `$v->customField !== null`; multi-choice `Collection` values normalized to arrays), then syncs relations only for keys that are `array_key_exists` (so an absent key means "don't touch", not "clear"). `CreateTask` syncs only non-null keys.
**Invariant:** Count-equality, not `exists`: one foreign id among many fails the whole batch (fail-closed), and duplicate ids in the input cannot inflate the count past the check. Owner-as-assignee must work without a pivot row. A partial custom-field patch must never null untouched fields — merge before save, never pass the raw partial map to a full-replace writer.
**Probe:** `tests/Feature/Support/TenantFkValidatorAssertOwnedManyTest.php` (5 cases: all-owned pass, one-foreign-id throw, empty-array skip, no-current-team throw, duplicate-id handling); `tests/Feature/Support/TenantFkValidatorAssertUsersInWorkspaceTest.php` (member pass, outsider throw, owner-as-assignee pass); `tests/Feature/Chat/CrossTenantFkTest.php` (cross-tenant `company_id` rejected through the real `UpdateOpportunity`/`CreatePeople` actions, stored value unchanged).

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "TenantFkValidator assertOwnedMany assertUsersInWorkspace CustomFieldMerger merge saveCustomFields previousAssigneeIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the count-equality FK guard (dedupe → single team-scoped count → exact-match or throw) for any action accepting id arrays, and the member-set-plus-owner check for user references. Adopt merge-before-save for any EAV/partial-patch surface whose writer nulls absent keys, including filtering orphaned value rows. Adapt the Laravel ValidationException shape and the sync-per-key semantics to your framework. Omit the specific field enums. Companion to `deferred-assignee-notification.md` (consumes `previousAssigneeIds` captured here) and `llm-customfield-label-bridge.md` (the assistant-plane twin of the same validation concern).
