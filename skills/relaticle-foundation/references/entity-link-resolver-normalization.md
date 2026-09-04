<!-- capsule-v2 -->
# EntityLinkResolver normalized batch matching — how do CSV strings become record ids across columns, team members, and custom-field JSON values?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** how is value→record-id resolution made consistent (case-insensitive, trimmed, cached, tenant-safe) over three different storage strategies?

## One resolver, three backends, normalize-at-the-boundaries
**Path/Symbol:** `packages/ImportWizard/src/Support/EntityLinkResolver.php:batchResolve` (:82-111) with `resolveViaColumn` (:141-150), `resolveViaTeamMember` (:156-166), `resolveViaCustomField`+`resolveViaJsonColumn` (:172-305), and `rejectInaccessibleEntities` (:214-233).
**Signature:** `batchResolve(EntityLink $link, MatchableField $matcher, array<string> $uniqueValues): array<string, int|string|null>`; per-link-matcher cache key `"{link.key}:{matcher.field}"`.
**Data Shape:** input: unique raw strings; output map original-value → id|null. Backend chosen by `match(true)` on the link/matcher: User target → team-member pivot query; `custom_fields_*` prefix → CustomFieldValue table; default → plain model column pluck.

### Decisive source
```php
$results = match (true) {
    $link->targetModelClass === User::class      => $this->resolveViaTeamMember($field, $uniqueValues),
    $this->isCustomField($field)                 => $this->resolveViaCustomField($link, $field, $uniqueValues),
    default                                      => $this->resolveViaColumn($link, $field, $uniqueValues),
};
$normalizedResults = [];
foreach ($results as $dbValue => $id) {
    $normalizedResults[$this->normalizeForComparison((string) $dbValue)] = $id;   // mb_strtolower(trim)
}
foreach ($uniqueValues as $value) {
    $matchedId = $normalizedResults[$this->normalizeForComparison($value)] ?? null;
    $resolved[$value] = $matchedId;
    $this->cache[$cacheKey][$value] = $matchedId;     // cache NEGATIVE results too
}
```
And the sync guard:
```php
// Drop matches whose owning entity cannot be loaded for write (soft-deleted
// or another team). The matcher reads custom_field_values directly, bypassing
// scopes; the executor loads records through the default-scoped model query,
// so an unfiltered match becomes a silently skipped row.
private function rejectInaccessibleEntities(string $modelClass, array $valueToEntityId): array
```

**Flow:** normalize inputs (trim; blank→null) → cache check → dispatch backend → normalize BOTH sides of the comparison to `mb_strtolower(trim)` → write every result incl. misses into the per-link cache → return. JSON backend fans array-or-scalar json_value through `json_each`(sqlite)/`jsonb_array_elements_text`(pgsql)/`JSON_TABLE`(mysql) per driver, chunks of 5000 lowercased placeholders, first-seen wins per key.
**Invariant:** normalization is applied symmetrically to DB values and CSV values — case differences never split identities. Negative lookups are cached (no repeated misses hammer the DB). Every custom-field match is re-checked against a scoped, writable target query so the resolver never promises an id the executor cannot load.
**Probe:** `tests/Feature/ImportWizard/Support/EntityLinkResolverTest.php` (:17 member-by-email via pivot, :32 owner resolved, :59 non-member → null, :73 batch). Executor-side link tests: `ExecuteImportJobTest.php` :295/:472/:497/:533/:555/:608.
**Coverage caveat:** JSON-dialect SQL branches verified by source read only (test suite runs against sqlite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "EntityLinkResolver batchResolve rejectInaccessibleEntities resolveViaJsonColumn", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the three-backend resolver with boundary normalization and negative-result caching; the accessibility re-check whenever a matcher reads storage the executor reads differently. Adapt backends to your relation shapes (pivot/column/EAV-json). Omit the vendor-specific SQL functions if your engine differs — keep the normalize-both-sides contract.
