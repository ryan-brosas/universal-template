<!-- capsule-v2 -->
# Auto-create related records — match-or-create with dedup and matcher-field backfill

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** When a CSV references a related entity that doesn't exist yet, when may the importer create it — and how are duplicates and the matching value itself handled?

## resolveGroupedMatches / resolveCreationMatch / populateMatchingCustomField
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `resolveGroupedMatches()` (:953-1002), `resolveCreationMatch()` (:1005-1014), `populateMatchingCustomField()` (:1017-1067), `resolveRecordFieldByName()` (:1074-1093).
**Signature:** `resolveGroupedMatches(Collection $matches, EntityLink $link, array $context): ?string`
**Data Shape:** Dedup key `"{link->key}:".mb_strtolower($creationName)`; auto-created rows get `team_id`+`creator_id` from context and `creation_source = IMPORT`.

### Decisive source
```php
// Record custom fields should never auto-create target entities, only match existing ones.
if ($link->storageType === EntityLinkStorage::CustomFieldValue) {
    return $this->resolveRecordFieldByName($link, $creationName, $context, $dedupKey);
}
```
Priority rule (:1007-1013): an explicit `behavior === Create` match wins; otherwise the FIRST MatchOrCreate create-match is used. After creating a person by email or company by domain (:2235/:2270 tests), the matched VALUE is written into the new record's corresponding custom field via the shared pending-value buffer — but "does not populate custom field when auto-creating via name matcher" (:2305), because only identity fields (email/domain) deserve materialization.

**Flow:** grouped relationship matches per link key → existing-ID wins immediately → else creation candidate (Create behavior first, then MatchOrCreate) → dedup cache hit returns prior id → CF-storage links NEVER create (match-only lookup) → real-entity links forceFill name/team/creator/source, save, backfill the matching CF value, cache id.
**Invariant:** The no-auto-create boundary for custom-field-stored relations is load-bearing (CF values are pointers, not registries); every auto-created record must carry provenance (`CreationSource::IMPORT`) so downstream can distinguish imported data.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:472 auto-create on unresolved link, :497 cross-row dedup, :533 MatchOnly refusal, :2331 dedup + CF backfill together).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "resolveGroupedMatches resolveCreationMatch populateMatchingCustomField createdRecords", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tiered auto-creation (existing > explicit-create > match-or-create) with per-name dedup, provenance stamping, and the pointer-fields-never-create rule. Adapt the identity-field backfill list. Omit CRM model specifics. Rich direct-test coverage including negatives.
