<!-- capsule-v2 -->
# Tenant-scoped array relationship validation — one data-aware rule prefetching a single batched id set with per-index errors

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you validate an array of relationship ids against a tenant scope with ONE query for the whole array, while still reporting exactly which array index was invalid?

## ArrayExistsForTeam + BaseUpdateTool wiring + attach/detach relationshipRules
**Path/Symbol:** `app/Rules/ArrayExistsForTeam.php` (whole, 88L): `setData()` (:26-33), `validate()` (:35-48), `prefetchValidIds()` (:50-77); wiring `app/Mcp/Tools/BaseUpdateTool.php` (whole, 110L): `schema()` (:60-73), `handle()` (:75-108); per-entity rule tables `app/Mcp/Tools/Task/UpdateTaskTool.php` `entityRules()` (:53-68), `app/Mcp/Tools/Task/AttachTaskToEntitiesTool.php` `relationshipRules()` (:48-63), `DetachTaskFromEntitiesTool.php` `relationshipRules()` (identical table).
**Signature:** `new ArrayExistsForTeam(string $table, string $arrayKey, int|string $teamId, string $column = 'id')` implementing `DataAwareRule, ValidationRule`; `validate(string $attribute, mixed $value, Closure $fail): void` runs once per array element under Laravel's `*` rule expansion.
**Data Shape:** Rule instance carries the table + the array key it lives under + the tenant id; a private `?array $validIds` memo (`array<string, true>`) is built lazily on the first element and invalidated in `setData()` whenever the submitted array changes.

### Decisive source
```php
public function setData(array $data): static
{
    if (Arr::get($this->data, $this->arrayKey) !== Arr::get($data, $this->arrayKey)) {
        $this->validIds = null;
    }
    $this->data = $data;
    return $this;
}
...
$this->validIds ??= $this->prefetchValidIds();
if (! isset($this->validIds[(string) $value])) {
    $fail('validation.exists')->translate();
}
```
`prefetchValidIds()` normalizes the submitted array (strings/ints only, stringified, deduped), then issues ONE `DB::table($table)->whereIn($column, $submitted)->where('team_id', $teamId)->pluck($column)` and returns an isset-friendly map. Empty input short-circuits to an empty valid set WITHOUT querying. Per-element `validate()` calls are therefore O(1) map lookups, and Laravel's `*` attribute expansion keeps the error keyed to the failing index (`company_ids.1`), which is exactly what an AI client needs to self-correct. The `setData` invalidation guard exists because Laravel reuses one rule instance across validator runs — a stale memo would accept ids from a previous payload. Assignees are the exception that proves the design: `'assignee_ids.*' => Rule::in($teamMemberIds)` (member ids come from `$team->allUsers()`, no DB rule needed). `BaseUpdateTool::handle()` merges `entityRules($user)` + `ValidCustomFields` custom-field rules, resolves the model by id, returns a typed not-found error, policy-checks `update`, unsets the id, and delegates to the SAME action class the API uses — the rules table is duplicated verbatim between update and attach/detach tools because each tool declares its own schema contract.
**Flow:** tool schema advertises `*_ids` arrays with omit-vs-`[]` semantics → validation runs the batched rule per element → cross-team id fails ONLY its own index → on pass, attach/detach apply `syncWithoutDetaching`/`detach` per key; update delegates to the action which syncs inside its transaction.
**Invariant:** The id set must be prefetched once per array (not per element) and re-prefetched when the payload changes; team scoping must be in the SAME query as existence (never check existence then ownership); failures must carry the array index.
**Probe:** `tests/Feature/Rules/ArrayExistsForTeamTest.php` (per-index failure `company_ids.1`, single-query prefetch via query log, empty-input zero-query, cross-team leak refusal, `setData` memo rebuild), `tests/Feature/Api/V1/TasksApiTest.php` (:194-208 mixed valid/invalid/duplicate array), `tests/Feature/Mcp/McpToolFeaturesTest.php` (cross-team attach/detach rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ArrayExistsForTeam prefetchValidIds setData relationshipRules BaseUpdateTool entityRules", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the data-aware batched existence rule for any array-of-ids field that must be tenant-scoped: one query, per-index errors, memo invalidation on payload change. Adapt the team-scope column and the member-ids exception to your auth model. Omit the Laravel `DataAwareRule` plumbing if your validator passes payload context differently. Direct tests pin all five rule behaviors plus the API and MCP surfaces; the duplicated rule tables across update/attach/detach tools are a deliberate schema-contract choice, not drift — caveat recorded.
