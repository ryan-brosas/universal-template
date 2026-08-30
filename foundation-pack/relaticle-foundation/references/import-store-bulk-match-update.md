<!-- capsule-v2 -->
# ImportStore bulk temp-table match update — how do tens of thousands of resolved matches land without a per-row UPDATE?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** how are precomputed value→id resolutions applied to stored rows in bulk while keeping unmatched semantics per action?

## TEMPORARY table + json_extract join, chunked inserts, finally-drop
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportStore.php:bulkUpdateMatches` (:101-142).
**Signature:** `bulkUpdateMatches(string $jsonPath, array<string,int|string|null> $resolvedMap, RowMatchAction $unmatchedAction): void`
**Data Shape:** `$resolvedMap`: lookup value (CSV cell string) → matched record id or null. Row table's `raw_data` is JSON text; `$jsonPath` is a SQLite json path like `$.email`. Output columns: `match_action` ('update'|'create'|'skip' from RowMatchAction enum), `matched_id`.

### Decisive source
```php
$connection->statement('CREATE TEMPORARY TABLE IF NOT EXISTS temp_match_results (
    lookup_value TEXT, match_action TEXT, matched_id TEXT)');
try {
    $inserts = collect($resolvedMap)->map(fn ($id, $value): array => [
        'lookup_value' => $value,
        'match_action' => $id !== null ? RowMatchAction::Update->value : $unmatchedAction->value,
        'matched_id'   => $id !== null ? (string) $id : null,
    ])->values()->all();
    foreach (array_chunk($inserts, 5000) as $chunk) {
        $connection->table('temp_match_results')->insert($chunk);
    }
    $connection->statement('UPDATE import_rows SET match_action = temp.match_action, matched_id = temp.matched_id
        FROM temp_match_results AS temp
        WHERE json_extract(import_rows.raw_data, ?) = temp.lookup_value
          AND import_rows.match_action IS NULL', [$jsonPath]);
} finally {
    $connection->statement('DROP TABLE IF EXISTS temp_match_results');
}
```

**Flow:** build temp rows carrying each value's verdict up front → chunked inserts (5k) → single set-based UPDATE joining on `json_extract(raw_data, jsonPath)` guarded by `match_action IS NULL` → drop temp table even on failure. Unmatched values arrive as null ids and are stamped with the caller's chosen fallback action (Create or Skip), so one statement handles both populations.
**Invariant:** the `match_action IS NULL` predicate makes the update idempotent/resumable — already-decided rows are never restamped; the finally-drop guarantees no temp residue after exceptions. Per-row PHP loops are avoided entirely; the DB does the join.
**Probe:** `tests/Feature/ImportWizard/Jobs/ResolveMatchesJobTest.php` (:98 "resolves Update when email matches existing record", :140 Skip-on-unmatched, :190 mixed matched/unmatched stamping, :173 reset-and-re-resolve).
**Coverage caveat:** full-mode graph cites this symbol clean (`no_recorded_issue`/`metadata_match`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "bulkUpdateMatches temp_match_results", limit: 6, fields: ["signature", "lines"] });
```

## Verdict
Adopt: resolve-then-bulk-apply — compute all matches in memory (or batch queries), stage them in a temp table, apply with one set-based UPDATE, always drop staging. Adapt chunk size and dialect (the UPDATE…FROM join form is SQLite-flavored; Postgres wants the same shape, MySQL needs different syntax). Omit nothing — the guard predicate is the reusable core.
