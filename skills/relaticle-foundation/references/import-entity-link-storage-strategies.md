<!-- capsule-v2 -->
# Entity-link storage strategies — one contract, three persistence shapes

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you persist a resolved relationship when different relations store it as FK column, pivot rows, or a custom-field value?

## EntityLink value object + strategy table
**Path/Symbol:** `packages/ImportWizard/src/Data/EntityLink.php` (whole, 334L): factories (:81-202), `getStorageStrategy()` (:292-299), `fromCustomField()` (:108-133); `packages/ImportWizard/src/Support/EntityLinkStorage/{ForeignKeyStorage,MorphToManyStorage,CustomFieldValueStorage}.php` (whole).
**Signature:** `EntityLinkStorageInterface { prepareData(array $data, EntityLink $link, array $resolvedIds): array; store(Model $record, EntityLink $link, array $resolvedIds, array $context): void }`
**Data Shape:** `EntityLink{key, source: Relationship|CustomField, targetEntity, targetModelClass, matchableFields[], storageType, label, allowMultiple, foreignKey?, morphRelation?, customFieldCode?, guesses[], sortOrder?}` — immutable Data object with `cloneWith()`-based fluent setters.

### Decisive source
```php
// ForeignKeyStorage::prepareData — write happens BEFORE save via the data array
$foreignKey = $link->foreignKey ?? $link->key.'_id';
$id = $resolvedIds[0] ?? null;
if ($id !== null) { $data[$foreignKey] = $id; }

// MorphToManyStorage::store — write happens AFTER save via syncWithoutDetaching
if (! method_exists($record, $relationName)) { return; }
$record->{$relationName}()->syncWithoutDetaching($resolvedIds);

// CustomFieldValueStorage::prepareData — writes through the CF attribute bridge
$data['custom_fields_'.$link->customFieldCode] = $resolvedIds[0];
```
Strategy memoization is static per enum value: `self::$storageStrategies[$this->storageType->value] ??= match (...) {...}`.

**Flow:** executor resolves relationships INSIDE the row transaction (`resolveEntityLinkRelationships` :908-947): each pending link's `prepareData` mutates the payload pre-save; after `$record->save()`, `storeEntityLinkRelationships` runs post-save `store()` for the strategies that need the persisted record. Record-type (`lookup_type`) custom fields are unified with real relations by `BaseImporter::entityLinks()` so the UI and executor treat both identically.
**Invariant:** The two-phase split (prepareData before save / store after save) is the whole porting point — FK and CF links must NOT call `$record->relations()->sync()` before the record exists, and morph pivots must NOT be stuffed into the attribute array.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:295 FK link on create, :555 MorphToMany store called after save, :628 multiple entity links).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "EntityLink getStorageStrategy prepareData store ForeignKeyStorage MorphToManyStorage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the interface pair (pre-save data mutation vs post-save persistence) for any multi-shape relation writer. Adapt the concrete trio to your relation types. Omit the hardcoded company/people/opportunity factory presets. Direct tests pin all three shapes.
