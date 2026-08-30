<!-- capsule-v2 -->
# EntityLink storage strategy trichotomy — how do three relationship kinds (FK / morphToMany / custom-field EAV) share one import-time resolution contract?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** where does each relationship kind get written, and why do FK links prepare data pre-save while others act post-save?

## Strategy objects chosen by enum, two-phase prepare/store
**Path/Symbol:** `packages/ImportWizard/src/Data/EntityLink.php:getStorageStrategy` (:292-299, static memoized match on EntityLinkStorage enum) + `Support/EntityLinkStorage/{EntityLinkStorageInterface,ForeignKeyStorage,MorphToManyStorage}.php`; call sites `ExecuteImportJob.php:resolveEntityLinkRelationships` (:908-947) + `storeEntityLinkRelationships` (:1122-1130).
**Signature:** `interface EntityLinkStorageInterface { prepareData(array $data, EntityLink $link, array $resolvedIds): array; store(Model $record, EntityLink $link, array $resolvedIds, array $context): void }`
**Data Shape:** resolved ids arrive as a non-empty list (single id for belongsTo). FK: `$data[$link->foreignKey ?? key.'_id'] = $resolvedIds[0]`. MorphToMany: `syncWithoutDetaching` via relation name (method_exists guard). CustomFieldValue: never auto-creates targets — match-only lookup by name, cached in `$createdRecords` dedup map.

### Decisive source
```php
public function getStorageStrategy(): EntityLinkStorageInterface
{
    return self::$storageStrategies[$this->storageType->value] ??= match ($this->storageType) {
        EntityLinkStorage::ForeignKey     => new ForeignKeyStorage,
        EntityLinkStorage::MorphToMany    => new MorphToManyStorage,
        EntityLinkStorage::CustomFieldValue => new CustomFieldValueStorage,
    };
}
```
Executor split (inside the row transaction):
```php
$storageStrategy = $link->getStorageStrategy();
$data = $storageStrategy->prepareData($data, $link, [$resolvedId]);   // FK mutates payload pre-save
$pending[] = ['link' => $link, 'strategy' => $storageStrategy, 'ids' => [$resolvedId]];
...after $record->save():
$this->storeEntityLinkRelationships($record, $pendingRelationships, $context); // pivot/EAV post-save
```

**Flow:** relationships grouped by link key → existing-match wins over creation-match → unresolved names may auto-create the target (name + team + creator + `CreationSource::IMPORT`) with cross-row dedup via `"{link.key}:{lowercased-name}"` map → strategy.prepareData folds ids into the attribute payload (FK only) → record saved → strategy.store syncs pivots (morph) or defers (FK no-op). Auto-create is refused for MatchOnly link definitions and for custom-field-record links (match existing only).
**Invariant:** FK identity travels WITH the save (atomic), pivot/EAV identity follows it (post-save, same transaction); auto-created targets are deduplicated process-wide so two CSV rows naming "Acme" share one company; a link whose matcher set is MatchOnly can never spawn records.
**Probe:** `ExecuteImportJobTest.php` (:295 company FK set on People create, :472 auto-create on unresolved link, :497 dedup across rows, :533 MatchOnly refuses creation, :555 morph store() called after save, :584 team/creation_source stamped, :628 multiple links per row).
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "getStorageStrategy resolveEntityLinkRelationships ForeignKeyStorage MorphToManyStorage", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the two-phase prepare/store strategy split and the enum-memoized strategy registry for any importer that must write several relationship shapes. Adapt the three strategies to your relation inventory. Omit CRM entity aliases and guess lists.
