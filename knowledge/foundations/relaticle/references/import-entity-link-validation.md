<!-- capsule-v2 -->
# Entity-link validation pass — resolve-time relationship previews written into row state

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** During column validation (before any execution), how do you preview which related records a row WILL link to and surface unresolvable values as reviewable errors?

## ValidateColumnJob entity-link branch
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ValidateColumnJob.php`: `validateEntityLink()` (:77-98), `writeEntityLinkRelationships()` (:104-171), `clearValidationForCorrectedDateFields()` (:173-186), `fetchUncorrectedUniqueValues()` (:189-197).
**Signature:** `writeEntityLinkRelationships(Import $import, Connection $connection, string $jsonPath, EntityLinkValidator $validator, array $uniqueValues, array $errorMap = []): void`
**Data Shape:** Row `relationships` JSON array of `RelationshipMatch{link key, id|null, behavior, matchField}`; per-value error map value→error|null.

### Decisive source
```php
$validValues = array_filter($uniqueValues, fn (string $v): bool => ($errorMap[$v] ?? null) === null);
$resolvedMap = $matcher->behavior === MatchBehavior::Create
    ? array_fill_keys($validValues, null)                    // will-create: placeholder match
    : $validator->getResolver()->batchResolve($link, $matcher, $validValues);
...
$match = $resolvedId !== null
    ? RelationshipMatch::existing($link->key, (string) $resolvedId, $behavior, $field)
    : RelationshipMatch::create($link->key, (string) $value, $behavior, $field);
```
Append-only SQL: `json_insert(COALESCE(relationships,'[]'), '$[#]', json(temp.relationship_json))` — MatchOnly misses are skipped entirely (no placeholder). Date-column re-validation clears stale errors ONLY for cells the reviewer corrected (`json_remove(... WHERE json_extract(corrections,?) IS NOT NULL`).

**Flow:** job fans out per column in a batch → entity-link columns take the dedicated branch: unique uncorrected values → batch validate/resolve → temp-table append of create/existing matches → execution later reads these previews instead of re-resolving. Corrected cells are excluded from re-validation so human fixes are never overwritten.
**Invariant:** Validation must be PRE-CORRECTION aware (never flag a cell the user already fixed) and relationship previews must distinguish existing-ID matches from intended creates so the executor can honor MatchOnly refusals.
**Probe:** `tests/Feature/ImportWizard/Jobs/ValidateColumnJobTest.php` (:422L suite incl. date-correction clearing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ValidateColumnJob writeEntityLinkRelationships clearValidationForCorrectedDateFields RelationshipMatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-time resolution previews persisted into row state — it makes the review UI honest and the executor dumb. Adapt JSON-append mechanics to your store. Omit Filament step components. Direct test coverage present.
