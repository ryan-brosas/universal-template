<!-- capsule-v2 -->
# Date-surface consistency — one timezone truth across picker, table, and infolist

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** When a vendor package renders custom-field datetimes itself, how do you stop the same value showing different times on different surfaces?

## DateTimeColumn / DateTimeEntry / DateFieldType overrides
**Path/Symbol:** `app/Filament/CustomFields/DateTimeColumn.php` (whole, 48L), `DateTimeEntry.php` (whole, 42L), `DateFieldType.php` (whole, 25L); registration `app/Providers/AppServiceProvider.php` (:440-461).
**Signature:** `CustomFieldsType::register(['date-time' => DateTimeFieldType::class, 'date' => DateFieldType::class]);`
**Data Shape:** Column hands Filament the raw Carbon state; entry passes format through untouched (null included) so the panel default wins.

### Decisive source
```php
/**
 * The package column formats the value itself and hands Filament a finished string,
 * so nothing downstream can still convert it — a date-time custom field renders the
 * stored UTC wall clock to every viewer, while the DateTimePicker that wrote it and
 * the infolist entry that echoes it both convert. Same value, three surfaces, two
 * answers.
 *
 * Give Filament the Carbon instance instead and let its own dateTime() formatter run:
 * that is the path that reads FilamentTimezone...
 */
```
The date-only carve-out (both files): "a bare date has no time of day to shift, so converting one would move it a day for every viewer west of UTC" — `date` swaps ONLY the infolist entry (the package's hardcoded literal fallback), never its table column. Entry docblock: "Written out rather than subclassed because the package entry is final."

**Flow:** provider re-registers two vendor field types at boot → `date-time` gets BOTH overrides (column + entry) so writer/reader/table all convert via FilamentTimezone → `date` gets only the entry swap → null formats propagate so each panel's own default applies without this code knowing which panels exist.
**Invariant:** Never pre-format a datetime into a string before handing it to the rendering layer that owns timezone conversion; date-ONLY values must skip tz conversion entirely.
**Probe:** No dedicated upstream test file for these three classes at this pin (grep found none) — coverage caveat; behavior documented in-source and cross-pinned by the import timezone suite (:2542 date-only non-shift rule).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "DateTimeColumn DateTimeEntry DateFieldType CustomFieldsType register", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "renderer owns conversion" as the invariant when integrating third-party field packages; keep date-only values conversion-free. Adapt registration mechanism to your component system. Coverage caveat recorded (no isolated tests).
