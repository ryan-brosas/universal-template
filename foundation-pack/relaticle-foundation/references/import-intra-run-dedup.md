<!-- capsule-v2 -->
# Intra-import dedup — Create rows promoting to Update via a normalized value cache

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you stop a CSV containing the same company five times from creating five companies, without a second DB pass?

## matchableValueCache promote-on-hit
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `lookupMatchableValueCache()` (:859-868), `registerInMatchableValueCache()` (:870-875), `normalizeMatchableValues()` (:885-901), promotion block in `processRow()` (:240-251).
**Signature:** `normalizeMatchableValues(ImportRow $row, MatchableField $matchField, string $sourceColumn): array<string> // lowercased, trimmed, non-empty parts`
**Data Shape:** `$matchableValueCache: array<normalizedValue, recordId>` and `$createdRecords: array<"{linkKey}:{name}", id>` (second cache for auto-created related entities); `$dedupedRows: list<int>` for persistence.

### Decisive source
```php
if ($effectiveAction === RowMatchAction::Create
    && $matchField instanceof MatchableField
    && $matchSourceColumn !== null
) {
    $cachedRecordId = $this->lookupMatchableValueCache($row, $matchField, $matchSourceColumn);
    if ($cachedRecordId !== null) {
        $effectiveAction = RowMatchAction::Update;      // PROMOTE, don't skip
        $effectiveMatchedId = $cachedRecordId;
        $this->dedupedRows[] = $row->row_number;
    }
}
```
Registration happens inside the create transaction right after save (:296-298). Multi-value fields (email/phone) split on commas so `a@x.com, b@x.com` collides with a later row carrying either part alone.

**Flow:** row marked Create → all its normalized matchable parts checked against the cache → any hit rewrites the row's effective action/id BEFORE the write branch → promotion is PERSISTED back to the store (`flushProcessedRows` updates `import_rows.match_action` for deduped rows) so a job retry sees consistent state → cache registration only fires on the non-repeat create path.
**Invariant:** Promotion must happen before required-field assertion and payload build use `$isCreate` — otherwise the promoted update would wrongly demand create-required fields. The store-level rewrite keeps dedup idempotent across retries.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:2038 same-email creates deduped, :2062 different values not deduped, :2081 multi-value field dedup, :2102 domain-keyed dedup).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "matchableValueCache lookupMatchableValueCache registerInMatchableValueCache normalizeMatchableValues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt promote-to-update (never drop-the-row) intra-batch dedup with persisted action rewrites. Adapt normalization strength (case-fold + trim + multi-part split here) and the persistence medium. Omit CRM match-field presets. Direct tests cover single/multi/domain keys plus the negative case.
