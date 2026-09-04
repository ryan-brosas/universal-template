<!-- capsule-v2 -->
# Match resolution ladder — reset, unique-value lookup, behavior-driven remainder

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you decide Create-vs-Update-vs-Skip per row when matching CSV values against existing records?

## MatchResolver + priority match-field selection
**Path/Symbol:** `packages/ImportWizard/src/Support/MatchResolver.php` (whole, 154L): `resolve()` (:27-43), `resetPreviousResolutions()` (:45-52), `resolveWithLookup()` (:64-86), `resolveMultiValueField()` (:131-153); `packages/ImportWizard/src/Importers/BaseImporter.php`: `getMatchFieldForMappedColumns()` (:266-271).
**Signature:** `resolve(): void`; `getMatchFieldForMappedColumns(array $mappedFields): ?MatchableField`
**Data Shape:** `MatchableField{field, behavior: Create|MatchOnly|MatchOrCreate, priority, multiValue}`; result columns on every row: `match_action`, `matched_id`.

### Decisive source
```php
public function resolve(): void {
    $this->resetPreviousResolutions();                       // NULL out action+id for ALL rows
    ...
    if ($matchField instanceof MatchableField && $matchField->behavior !== MatchBehavior::Create) {
        $this->resolveWithLookup($matchField, $mappings);    // batch-resolve distinct values
    }
    $this->markRemainingAs(RowMatchAction::Create);           // everything still NULL becomes Create
}
```
Lookup side: `DISTINCT json_extract(raw_data, ?)` over undecided rows → `EntityLinkResolver::batchResolve` → temp-table join writes Update+id or (per behavior) Skip/Create. Multi-value fields explode comma parts, batch-resolve the union, then map each original CSV string to its FIRST resolved part.

**Flow:** highest-priority matchable field whose target column is actually MAPPED wins (`sortByDesc(priority)->first(mapped)`) → previous resolutions wiped wholesale (idempotent re-resolve) → unresolved values become Skip under MatchOnly, Create otherwise → executor additionally promotes later duplicate Creates to Updates via its intra-run cache.
**Invariant:** Resolution is a full-recompute pass, not incremental — reset-before-write is what makes re-running the resolver safe; the "mark remaining" step must run even when no lookup happened so every row leaves with an explicit action.
**Probe:** `tests/Feature/ImportWizard/Jobs/ResolveMatchesJobTest.php` (:256L whole suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "MatchResolver resolve markRemainingAs getMatchFieldForMappedColumns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reset→lookup→default-remainder as the shape of any batch dedup/match pass, plus priority-sorted "only consider fields the user actually mapped". Adapt behaviors to your domain vocabulary. Omit CSV specifics. Direct tests green upstream.
