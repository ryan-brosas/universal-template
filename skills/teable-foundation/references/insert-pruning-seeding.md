<!-- capsule-v2 -->
# Insert-stage oneMany pruning & conditional seeding — why does a fresh row skip most of its own link fields, and which fields must be force-seeded anyway?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** On INSERT, which computed fields can be safely dropped from the plan (null→null churn) and which are invisible to dependency scanning yet still required for correct stored reads?

## filterOneManyLinksOnInsert + conditional/context-free seeding in planStage
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedUpdatePlanner.ts` — `filterOneManyLinksOnInsert` (:1281–1330), conditionalRollup/conditionalLookup insert seeding (:613–660), context-free formula inclusion (:663–681), fallback fixed-point edge synthesis (:684–733).
**Signature:** `filterOneManyLinksOnInsert(fieldsById, computedFieldIds, seedTableId, explicitlyChangedFieldIds): Set<string>`.
**Data Shape:** FieldMeta `{id, tableId, type, options: {relationship: 'manyOne'|'oneMany'|'oneOne'|'manyMany', symmetricFieldId?}, conditionalOptions?: {foreignTableId, lookupFieldId, conditionFieldIds, filterDto}}`.

### Decisive source
```ts
// Skip seed-table link fields unless the user explicitly set the link value.
if (meta.type === 'link' && meta.tableId.equals(seedTableId)) continue;   // filtered out
// ...preceded by two keep-guards:
if (explicitlyChangedFieldIds.has(fieldId)) { filtered.add(fieldId); continue; }
if (symmetricFieldIdsOfExplicitLinks.has(fieldId)) { filtered.add(fieldId); continue; }
```
```ts
// INSERT: conditional fields depend only on foreign-table changes and can be
// "invisible" to same-record dependency scanning. Ensure they're computed for
// newly inserted records so stored reads are correct.
if (context.changeType === 'insert' && context.table) {
  for (const field of context.table.getFields()) {
    const fieldType = field.type().toString();
    if (fieldType !== 'conditionalRollup' && fieldType !== 'conditionalLookup') continue;
    ...
    affectedFieldIds.add(fieldId);
  }
}
```

**Flow:** on INSERT the FK of a oneMany link lives in the FOREIGN table — a brand-new row cannot have children pointing at it, so recomputing those link fields yields null→null noise: drop every seed-table link field EXCEPT (a) fields the user explicitly set and (b) symmetric twins of explicitly-set links. In parallel, three seeding passes ADD fields scanning would miss: conditional rollups/lookups (their filter references foreign rows only), context-free formulas (`NOW()`-style, zero dependencies), and — during schema conversion windows when reference rows are unavailable — a fixed-point walk synthesizing same-record edges for any formula reachable from the seeds.
**Invariant:** Pruning is keyed on FK LOCATION (which table holds the foreign key), not link direction naming alone; the two keep-guards prevent dropping user-visible values. Seeding is mandatory because stored reads (generated columns/materialized values) have no fallback computation path at query time.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedUpdatePlanner.spec.ts` (insert-plan describes pinning oneMany pruning with explicit-set keeps, conditional seeding, and context-free formula inclusion across :29–1015).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "filterOneManyLinksOnInsert conditionalOptions context-free formula seed", limit: 10 });
```

## Verdict
Adopt FK-location-keyed insert pruning with explicit-value + symmetric keeps, and the three forced-seeding passes for scan-invisible fields; adapt field-type names to host taxonomy; omit nothing else — the logic is self-contained around the planner.
