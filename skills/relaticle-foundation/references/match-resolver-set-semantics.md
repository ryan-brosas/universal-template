<!-- capsule-v2 -->
# MatchResolver set-based row disposition — how does every imported row get a Create/Update/Skip verdict before execution starts?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** what is the exact order of operations that assigns match actions to all rows, idempotently, including multi-value lookup cells?

## Reset → lookup → mark-remaining-as-fallback
**Path/Symbol:** `packages/ImportWizard/src/Support/MatchResolver.php:resolve` (:27-43) + `resolveWithLookup` (:64-86) + `resetPreviousResolutions` (:45-52); called from `packages/ImportWizard/src/Jobs/ResolveMatchesJob.php:handle` (:35-51, `#[Timeout(120)] #[Tries(1)]`, queue `imports`, early-return when `batch()?->cancelled()`).
**Signature:** `final readonly class MatchResolver { __construct(ImportStore $store, Import $import, BaseImporter $importer); resolve(): void }`
**Data Shape:** mappings are `ColumnData` rows (source CSV header ↔ target field or entity link); the match field comes from `BaseImporter::getMatchFieldForMappedColumns` = highest-`priority` MatchableField whose `field` is among mapped targets; behavior ∈ {Create, MatchOnly, MatchOrCreate}.

### Decisive source
```php
public function resolve(): void
{
    $this->resetPreviousResolutions();          // match_action=NULL, matched_id=NULL for ALL rows
    $matchField = $this->importer->getMatchFieldForMappedColumns($mappedFieldKeys);
    if ($matchField instanceof MatchableField && $matchField->behavior !== MatchBehavior::Create) {
        $this->resolveWithLookup($matchField, $mappings);
    }
    $this->markRemainingAs(RowMatchAction::Create);   // everything still NULL becomes Create
}

private function extractUniqueValues(string $jsonPath): array
{
    return $this->store->query()
        ->whereNull('match_action')
        ->selectRaw('DISTINCT json_extract(raw_data, ?) as value', [$jsonPath])
        ->pluck('value')->filter()->values()->all();
}
```

**Flow:** wipe previous verdicts (re-resolution must be total) → if a non-Create-behavior matcher is mapped: DISTINCT-scan unique lookup values straight out of the JSON column → `EntityLinkResolver::batchResolve` (or multi-value fan-out: explode comma cells, resolve parts once, first hit wins back per cell) → `ImportStore::bulkUpdateMatches` stamps Update/unmatched-action → `markRemainingAs` closes the set so no row leaves resolution undecided.
**Invariant:** after `resolve()` returns, NO row has `match_action IS NULL` — the executor can rely on total disposition. Reset-before-resolve makes the whole pass idempotent across job retries (Tries=1 here, but the wizard UI can re-run resolution).
**Probe:** `tests/Feature/ImportWizard/Jobs/ResolveMatchesJobTest.php` (:83 no-match-field ⇒ all Create; :98 email match ⇒ Update; :140 MatchOnly miss ⇒ Skip; :154 relationships column preserved through reset; :173 re-resolution resets prior stamps; :214 comma-separated multi-value cell resolves to existing record).
**Coverage caveat:** none beyond the standard best-effort note; all cited symbols covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "MatchResolver markRemainingAs extractUniqueValues", limit: 6, fields: ["signature", "lines"] });
```

## Verdict
Adopt: two-phase disposition (decide everything, then execute) with a guaranteed-total fallback stamp; DISTINCT-over-JSON to shrink lookup work to unique values. Adapt the match-field priority rule and behaviors to your domain vocabulary. Omit CRM-specific entity-link plumbing (see entity-link-resolver capsule for that half).
