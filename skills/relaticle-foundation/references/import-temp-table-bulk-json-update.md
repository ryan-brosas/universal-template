<!-- capsule-v2 -->
# JSON-path bulk row mutation — temp-table join instead of per-row UPDATE

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you update thousands of rows keyed by a value buried inside a JSON column without N queries?

## Temp-table + json_extract set-update (ImportStore.bulkUpdateMatches / ValidateColumnJob.updateValidationErrors)
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportStore.php`: `bulkUpdateMatches()` (:101-142); `packages/ImportWizard/src/Jobs/ValidateColumnJob.php`: `updateValidationErrors()` (:236-268), `writeEntityLinkRelationships()` (:104-171).
**Signature:** `bulkUpdateMatches(string $jsonPath, array $resolvedMap, RowMatchAction $unmatchedAction): void`
**Data Shape:** `$jsonPath` = `'$.<column>'` SQLite path syntax; `$resolvedMap` = lookupValue→id|null; unmatched rows get the behavior-derived action (`MatchOnly`⇒Skip, else Create). Temp tables: `temp_match_results(lookup_value, match_action, matched_id)`, `temp_validation(raw_value, validation_error)`, `temp_relationships(lookup_value, relationship_json)`.

### Decisive source
```php
$connection->statement('
    UPDATE import_rows
    SET match_action = temp.match_action,
        matched_id  = temp.matched_id
    FROM temp_match_results AS temp
    WHERE json_extract(import_rows.raw_data, ?) = temp.lookup_value
      AND import_rows.match_action IS NULL          -- only undecided rows
', [$jsonPath]);
...
} finally {
    $connection->statement('DROP TABLE IF EXISTS temp_match_results');
}
```
The validation twin is richer — one statement both clears and sets: `SET validation = CASE WHEN temp.validation_error IS NULL THEN json_remove(COALESCE(validation,'{}'), ?) ELSE json_set(COALESCE(validation,'{}'), ?, temp.validation_error) END ... AND json_extract(import_rows.corrections, ?) IS NULL`. The relationship writer appends with `json_insert(COALESCE(relationships,'[]'), '$[#]', json(temp.relationship_json))`.

**Flow:** chunk inserts (5,000/bulk-map batch; validation inserts whole result set) into TEMP table → single FROM-join UPDATE over `json_extract` equality guarded by "undecided"/"uncorrected" predicates → `finally` drops the temp table even on throw → validation job wraps its variant in `$connection->transaction(...)`.
**Invariant:** Every temp-table write must be paired with a DROP in `finally`; the WHERE clause must carry the idempotence predicate (only rows whose decision is still NULL / whose cell was not corrected) so re-runs never clobber human review.
**Probe:** `tests/Feature/ImportWizard/Jobs/ResolveMatchesJobTest.php` (:256L suite) + `ValidateColumnJobTest.php` (:422L).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "bulkUpdateMatches temp_match_results json_extract update import_rows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the temp-table-join-over-JSON pattern for any set-based JSON-column mutation in SQLite; it converts O(N) round-trips into two statements and keeps atomicity. Adapt the JSON dialect functions if targeting Postgres (`jsonb_set` family). Omit the specific domain columns. Direct tests cover the resolve path end-to-end.
