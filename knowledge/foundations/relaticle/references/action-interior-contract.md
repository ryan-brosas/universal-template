<!-- capsule-v2 -->
# Action-interior contract — one readonly action class per CRUD verb composing policy, tenant-FK, merge, transaction, and eager-load

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** When web UI, REST API, and MCP tools all mutate the same entities, where does the shared write contract live so the three surfaces cannot drift?

## CreateCompany / UpdateCompany / CreateOpportunity / UpdateOpportunity / ListCompanies / DeleteCompany
**Path/Symbol:** `app/Actions/Company/CreateCompany.php` (whole, 36L), `app/Actions/Company/UpdateCompany.php` (whole, 36L), `app/Actions/Opportunity/CreateOpportunity.php` (whole, 43L), `app/Actions/Opportunity/UpdateOpportunity.php` (whole, 41L), `app/Actions/Company/ListCompanies.php` (whole, 79L), `app/Actions/Company/DeleteCompany.php` (whole, 17L); twins under `app/Actions/{Task,Note,People}/` (CreateTask/UpdateTask read in run 7).
**Signature:** `execute(User $user, array $data, CreationSource $source = CreationSource::WEB): Model` (create); `execute(User $user, Model $model, array $data): Model` (update); `execute(User $user, int $perPage = 15, bool $useCursor = false, array $filters = [], ?int $page = null, ?Request $request = null): CursorPaginator|LengthAwarePaginator` (list).
**Data Shape:** Every action is `final readonly`. Create/update take a raw array, shape it with `Arr::only($data, [whitelist])`, stamp `creation_source` (create only), and return the model eager-loaded with `customFieldValues.customField.options` — the exact shape the V1 resources and MCP tool responses serialize.

### Decisive source
```php
abort_unless($user->can('create', Company::class), 403);
TenantFkValidator::assertUserInWorkspace($user, $data, ['account_owner_id']);
$attributes = Arr::only($data, ['name', 'account_owner_id', 'custom_fields']);
$attributes['creation_source'] = $source;
$company = DB::transaction(fn (): Company => Company::query()->create($attributes));
return $company->load('customFieldValues.customField.options');
```
The update twin inserts one extra stage — `$attributes = CustomFieldMerger::merge($company, $attributes)` — before the same transaction, because a partial update must not wipe custom fields the payload omitted. Opportunity actions swap the FK check to `assertOwned($user, $data, ['company_id' => Company::class, 'contact_id' => People::class])` (scalar FKs, class-keyed map) instead of the user-in-workspace check. List actions are the read twin: policy `viewAny` → Spatie QueryBuilder over `Model::query()->withCustomFieldValues()->whereBelongsTo($user->currentTeam)` → allow-listed filters (partial name, `custom_fields` via `CustomFieldFilter`, callback date ranges, relationship scopes), fields, includes (with `AllowedInclude::count` for the `*Count` aggregates), dynamic custom-field sorts from `CustomFieldFilterSchema::allowedSorts`, `defaultSort('-created_at')` plus a deterministic `orderBy('id')` tiebreak, and a `useCursor` flag switching between cursor and offset pagination. Delete is deliberately minimal: policy gate + `delete()` (soft deletes) — no transaction, no side effects.
**Flow:** caller (Filament page, API controller, or MCP tool) → policy abort → tenant-FK validation → attribute whitelist (+ merge on update) → transaction → eager-load → return. The `CreationSource` argument defaults to WEB so human callers never pass it; API controllers pass API, MCP tools pass MCP (provenance capsule).
**Invariant:** All three surfaces must delegate to the SAME action class — the action is the only place policy, tenant scoping, custom-field merge, and transactionality live; the return shape must always carry the eager-loaded custom-field relations or the resource layer silently renders empty custom_fields.
**Probe:** `tests/Feature/Api/V1/TasksApiTest.php` (`mutates` the four task actions; create/update/delete/list, team scoping, cross-tenant relationship rejection), `tests/Feature/Chat/CrossTenantFkTest.php`, `tests/Feature/Chat/CreateCompanyOwnerScopingTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreateCompany UpdateCompany CreateOpportunity ListCompanies TenantFkValidator CustomFieldMerger execute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the readonly-action-per-verb contract with the fixed five-stage composition (policy → tenant-FK → whitelist/merge → transaction → eager-load) as the single write funnel for every surface. Adapt the FK-validator variants to your relation shapes (scalar vs array, workspace-member vs owned-record). Omit the Spie/QueryBuilder specifics if your list plane differs. Direct tests pin the task surface end-to-end through the API; company/opportunity action interiors are pinned indirectly through the same controllers and the cross-tenant suites — caveat recorded.
