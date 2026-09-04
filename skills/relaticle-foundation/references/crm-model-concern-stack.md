<!-- capsule-v2 -->
# CRM model concern stack — attribute-declared fillable/observers, EAV-aware activity logging, morphable tasks

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How are the five CRM entity models composed so tenancy, EAV custom fields, audit logging, and board ordering stay uniform — and what does the activity log deliberately exclude?

## One concern stack shared by all five entities
**Path/Symbol:** `app/Models/Opportunity.php` (118L), `app/Models/Task.php` (156L), `app/Models/Note.php`, `app/Models/People.php`, `app/Models/Company.php` (same stack); shared concerns `app/Models/Concerns/{HasTeam,BelongsToTeamCreator,HasCreator,HasNotes}.php`, tenancy scope `app/Models/Scopes/TeamScope.php`; export model `app/Models/Export.php` (18L).
**Signature:** every entity: `use HasUlids; use SoftDeletes; use SortableTrait; use UsesCustomFields (implements HasCustomFields); use LogsActivity (implements HasTimeline via InteractsWithTimeline); use HasTeam; use BelongsToTeamCreator + HasCreator;` plus `#[Fillable([...])]` and `#[ObservedBy(...)]` PHP attributes instead of `$fillable`/observer registration.
**Data Shape:** `TeamScope::apply` = `whereBelongsTo($user->currentTeam)` with an unauthenticated fallback of `whereRaw('1 = 0')` (fail-closed: no session ⇒ no rows, not all rows). Task relations: `assignees()` belongsToMany User; `companies()/people()/opportunities()` morphedByMany over the `taskable` morph, with `#[Scope] forCompany/forPerson/forOpportunity` whereHas helpers. Opportunity: `company()`/`contact()` belongsTo, `tasks()` morphToMany. `Export` extends Filament's `FilamentExport` adding only `HasUlids`.

### Decisive source
```php
public function getActivitylogOptions(): LogOptions
{
    return LogOptions::defaults()
        ->logAll()
        ->logOnlyDirty()
        ->dontLogEmptyChanges()
        ->logExcept([
            'id', 'team_id', 'creator_id', 'creation_source', 'custom_fields',
            'created_at', 'updated_at', 'deleted_at', 'order_column',
        ])
        ->useLogName('crm')
        ->setDescriptionForEvent(fn (string $eventName): string => $eventName);
}
```
The exclusion list is the porting payload: infrastructure columns (ids, tenancy, timestamps, soft-delete marker, board `order_column`) and the whole `custom_fields` JSON are never logged — the EAV values live in `custom_field_values` rows with their own lifecycle, and logging the JSON blob would duplicate every custom-field write into the activity log. Board ordering rides `SortableTrait` with `public array $sortable = ['order_column_name' => 'order_column', 'sort_when_creating' => true]` (Task declares it explicitly; spatie/eloquent-sortable maintains a dense integer order), while the kanban pages write float positions into the same column (see `kanban-eav-board-move.md`). `#[Fillable(['creation_source'])]` (Opportunity) vs `#[Fillable(['user_id','title','creation_source'])]` (Task) shows the allowlist kept minimal — mass assignment stays narrow, everything else is set through actions/relations.

**Flow:** entity create (ULID key, team + creator stamped via concerns, creation_source defaulted to `CreationSource::WEB` via `protected $attributes`) → custom fields as EAV rows → edits logged dirty-only under log name `crm` → soft deletes keep timeline history → timeline rendered by `TimelineBuilder::make($this)->fromActivityLog(mergedRenderer: 'merged-activity')`.
**Invariant:** Tenancy is fail-closed (no authenticated user ⇒ zero rows). Activity log records business fields only — never tenancy, ordering, or the custom-fields blob. All five entities share the identical stack, so a new CRM entity gets tenancy, EAV, logging, ordering, and timeline by composition, not per-model reimplementation.
**Probe:** `tests/Feature/Filament/App/Pages/OpportunitiesBoardTest.php` (tenancy exclusion + order_column behavior through the board); `tests/Feature/Chat/AllCustomFieldsViaChatTest.php` (EAV read/write through the shared custom-field bridge); `tests/Feature/Notifications/TaskAssignedEmailTest.php` (assignees pivot). Direct activity-log exclusion assertions were not found in the test suite — coverage caveat recorded; the exclusion list is source-confirmed at HEAD.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "getActivitylogOptions logExcept TeamScope whereBelongsTo SortableTrait order_column UsesCustomFields ObservedBy Fillable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the concern-stack composition for any multi-tenant entity family (one trait per cross-cutting concern, fail-closed tenancy scope) and the infrastructure-column exclusion list for activity logging — especially excluding the EAV blob when custom fields live in a side table. Adapt the attribute-declared `#[Fillable]`/`#[ObservedBy]` style to your framework version (they are Laravel 12 PHP attributes; older versions use properties). Omit the Filament Export subclass if you have no exports. Companion to `kanban-eav-board-move.md` (order_column consumer) and `customfields-model-swap-schema-resources.md` (the EAV binding side).
