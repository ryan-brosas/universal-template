<!-- capsule-v2 -->
# Queued-export timezone columns — how does a CSV produced by a sessionless queued job show datetimes in the requesting user's local time, including columns the framework pre-built?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When export rows are formatted in a queue worker with no session, where does each formatting site get the user's timezone from — and what do you do about plugin-provided columns that never pass through your formatter?

## Two-site timezone resolution + header-named zones + custom-field re-wrap
**Path/Symbol:** `app/Filament/Exports/BaseExporter.php` (`timezone`, `requestTimezone`, `timezoneFor`, `dateTimeColumn`, `customFieldColumns`, `modifyQuery`, constructor; 158L); exemplar `app/Filament/Exports/OpportunityExporter.php` (`getColumns`, 59L).
**Signature:** instance `timezone(): string` → `timezoneFor($this->export->user)`; static `requestTimezone(): string` → `timezoneFor(Auth::guard('web')->user())`; `timezoneFor(?Authenticatable $user)` → `$user instanceof User ? $user->effectiveTimezone() : config('app.timezone')`. `dateTimeColumn(name, label)` → `ExportColumn::make($name)->label($label.' ('.self::requestTimezone().')')->formatStateUsing(fn (?Carbon $state, BaseExporter $exporter) => $state?->setTimezone($exporter->timezone())->format('Y-m-d H:i:s'))`.
**Data Shape:** custom-field columns arrive pre-built from the CustomFields package (`CustomFields::exporter()->forModel(...)->columns()`); `customFieldColumns` maps them against an ENTITY-SCOPED field lookup (`CustomField::query()->forEntity(self::getModel())->get()->keyBy(getFieldName)`), converting only `date-time` type and trimming `date` type to `Y-m-d`.

### Decisive source
```php
// Values and headers resolve the same user from two different places because they
// are produced at two different moments: `formatStateUsing` runs inside the queued
// job, which has no session and reads the user off the export record, while
// `getColumns()` is static and only ever evaluated for labels during the interactive
// column-mapping step — Filament freezes those labels into the export's columnMap
// and writes the header row from that, never re-deriving it in the job.
```
```php
// Only `date-time` fields are converted. A date-only field has no time of day, so
// shifting it would move the calendar day for every viewer west of UTC; it is instead
// trimmed to `Y-m-d` to drop the `00:00:00` a Carbon cast invents.
```

**Flow:** export requested → constructor stamps `team_id` on the Export row from the web guard; static `getColumns()` runs once in-session, so datetime labels bake in `(Asia/Tokyo)`-style zone names via `requestTimezone()` → queued job formats rows with NO session, resolving the zone from `$this->export->user` instead → `customFieldColumns` re-wraps the package's pre-built columns because they bypass `dateTimeColumn` (a bare UTC datetime under a bare header in a file whose other columns say `(Asia/Tokyo)` is actively misleading) → `modifyQuery` scopes the export query to the stamped team.
**Invariant:** The zone name must appear in the header — a bare local timestamp is uninterpretable. Date-only fields are never timezone-shifted (that moves the calendar day for viewers west of UTC). The custom-field lookup is keyed per entity (codes are unique per entity type, not globally — `linkedin` exists on both Company and People). `timezoneFor` narrows to the `User` instance because the web guard is shared with the sysadmin panel's SystemAdministrator and an export row can outlive its author.
**Probe:** `tests/Feature/Filament/App/Exports/OpportunityExporterTest.php` (119L) + `TaskExporterTest.php` (220L) — export row stamped with team_id, team-scoped exports, system-seeded AND user-created custom fields present as columns, CSV generated with correct headers/data.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "BaseExporter dateTimeColumn customFieldColumns requestTimezone effectiveTimezone ExportColumn modifyQuery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-site resolution (export-record user in the job, session user for frozen labels), header-named zones, the date-vs-datetime conversion split, and entity-scoped re-wrapping of plugin-provided columns. Adapt Filament's Exporter/ExportColumn pair to your export runner; the invariant generalizes to any queued formatting job: resolve the human's zone from persisted state, never ambient session.
