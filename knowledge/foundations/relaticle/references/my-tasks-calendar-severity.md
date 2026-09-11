<!-- capsule-v2 -->
# My-tasks card — user-calendar severity boundaries, one-round-trip EAV metadata, container memoization

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you compute "overdue / today" for a per-user task widget when due dates are EAV custom fields stored in UTC and every user has a different calendar?

## Calendar-correct day boundaries over EAV data
**Path/Symbol:** `packages/Chat/src/Services/MyTasksService.php` (`MAX_ITEMS` :20, `forUser` :25-106, `resolveFieldMetadata` :108-143, `severity` :145-155, `MyTasksFieldMetadata` :162-169); consumer `app/Filament/Pages/Dashboard.php` (:114).
**Signature:** `forUser(User $user, Team $team): Collection<int, MyTaskItem>` where `MyTaskItem = {id, title, dueAt: ?Carbon, severity: ?string('overdue'|'today'|'tomorrow'), editUrl}`.
**Data Shape:** due date and status live in `custom_field_values` (EAV) under tenant-seeded custom fields with codes `due_date` (datetime_value) and `status` (string_value = option id); the "Done" option id is resolved by joining `custom_field_options` on `name='Done'`.

### Decisive source
```php
// "Overdue" and "today" are claims about the user's calendar, not the server's:
// bounded on UTC midnight a task due 23:00 UTC reads as overdue to anyone east
// of London for most of their working day. Compute the boundaries in the user's
// zone, then compare in UTC where the stored values live.
// Both boundaries are taken from local midnight before converting: a local day
// is 23 or 25 hours long across a DST transition, so adding a day to the already
// converted value would put the end of "today" an hour off twice a year.
$timezone = $user->effectiveTimezone();
$startOfToday = Date::now($timezone)->startOfDay()->utc();
$startOfDayAfter = Date::now($timezone)->startOfDay()->addDay()->utc();
```
```php
// One round-trip pulls both field IDs plus the Done option ID; memoized on the
// application container so concurrent dashboard renders in the same request
// reuse the result instead of refiring three lookups each time.
$cacheKey = MyTasksFieldMetadata::class.':'.$team->getKey();
if (app()->bound($cacheKey)) { return resolve($cacheKey); }
...
->selectRaw(implode(', ', [
    "MAX(CASE WHEN cf.code = 'due_date' THEN cf.id END) AS due_field_id",
    "MAX(CASE WHEN cf.code = 'status' THEN cf.id END) AS status_field_id",
    "MAX(CASE WHEN cf.code = 'status' THEN opt.id END) AS done_option_id",
]))
```
```php
// Done is an EAV option id, so exclusion is a whereNotExists, and the due date
// is LEFT-joined so undated tasks still appear (NULLS LAST in the sort).
$query->whereNotExists(function (Builder $sub) use ($meta): void {
    $sub->select(DB::raw(1))->from('custom_field_values as st')
        ->whereColumn('st.entity_id', 't.id')
        ->where('st.entity_type', 'task')
        ->where('st.custom_field_id', $meta->statusFieldId)
        ->where('st.string_value', $meta->doneOptionId);
});
```

**Flow:** resolve both EAV field ids + Done option id in one `MAX(CASE)` query (container-memoized per team) → join tasks ⋈ assignees scoped to team AND user → exclude Done via `whereNotExists` on the EAV table → left-join the due date, sort due ASC NULLS LAST then created DESC, cap at 5 → map each row to a severity by comparing the UTC-stored due instant against the two local-midnight-derived UTC boundaries → emit edit URLs pointing at the Filament index with `tableAction=edit&tableActionRecord=<id>` (the same modal convention the page-context resolver reads).
**Invariant:** Day boundaries always come from LOCAL midnight before any conversion — never `now()->addDay()` after converting — or DST days (23h/25h) misclassify tasks twice a year. A missing due field or status field degrades gracefully (no due column / no Done exclusion), it does not error. The query is team-scoped even when the user belongs to several teams.
**Probe:** `tests/Feature/Chat/MyTasksServiceTest.php` — assignment scoping (:102-122), all due dates + undated included (:124-149), Done excluded while no-status stays (:151-176), due-ASC sort with correct severities (:178-201), five-item cap (:203-217), no cross-team leak for a multi-team user (:219-234), Tokyo-vs-UTC same-instant divergence (:236-265), and the DST case: UK 25-hour day keeps a 23:30-local task "today" (:267-283).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "MyTasksService forUser resolveFieldMetadata severity startOfDay effectiveTimezone", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-boundary-from-local-midnight rule for ANY per-user "today/overdue" computation over UTC-stored timestamps — it is the whole DST story. Adopt single-round-trip `MAX(CASE)` metadata resolution + container memoization when several tenant-scoped schema lookups feed one query. Adopt `whereNotExists` exclusion + left-join inclusion for EAV-filtered lists. Adapt the seeded-field codes and Filament modal URL convention to your schema/UI. Omit the specific custom-fields vendor tables. Coverage caveat: Codebase Memory MCP was not connected this pass; evidence is direct source+test reads at the pinned HEAD.
