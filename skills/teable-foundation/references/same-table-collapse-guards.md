<!-- capsule-v2 -->
# Same-table batch collapse and skip guards — when do multi-level same-table formula chains run as ONE step, and when must they not?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How can N topo-sorted same-table formula steps collapse into a single CTE-batched UPDATE — and which four conditions force the planner to keep them separate?

## Collapse rule, JSON-target veto, dirty-count chunking, formula-only gate
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — `optimizeSameTableBatches` (:166–222) with `crossRecordDependentFieldIds` set :167–171; constants `SAME_TABLE_BATCH_CHUNK_TRIGGER = 1000` / `SAME_TABLE_BATCH_CHUNK_SIZE = 500` (:77–78); collapsed-step execution `executePreparedSteps` `collapsedBatchByStepKey` map (:884–901); formula-only ladder `formulaOnlyFieldLevelsResult` (:1094–1126) with non-formula early-exit `if (!field.type().equals(FieldType.formula())) return ok([]);` :1113–1115; JSON-target probe `hasJsonTargetColumns` (:1681–1721) + skip attributes `'json_target_column'` :1133–1135.
**Signature:** `optimizeSameTableBatches(plan: ComputedUpdatePlan): ComputedUpdatePlan`; collapsed key `${tableId}|${minLevel}`; execution via `SameTableBatchQueryBuilder.build({ table, fieldLevels, recordIds?, dirtyFilter })`.
**Data Shape:** plan carries `sameTableBatches[] {tableId, steps[], minLevel, maxLevel}`. Collapse replaces all batch steps with ONE step `{tableId, level: minLevel, fieldIds flattened in level order}`.

### Decisive source
```ts
// Only collapse batches that are purely same-record computed fields across levels.
const crossRecordDependentFieldIds = new Set(plan.edges.flatMap((edge) =>
  (edge.propagationTargetFieldIds ?? [edge.toFieldId]).map((fieldId) => fieldId.toString())));
const collapsibleBatches = plan.sameTableBatches.filter((b) => {
  if (b.steps.length <= 1) return false;
  return b.steps.every((step) =>
    !step.fieldIds.some((id) => crossRecordDependentFieldIds.has(id.toString())));
});
// ... collapsed step keeps dependency order:
const orderedSteps = [...batch.steps].sort((a, b) => a.level - b.level);
// dedupe field ids into one fieldIds array, level = batch.minLevel
```
```ts
// Execution side — four gates before the CTE batch builder is used:
if (formulaOnlyFieldLevelsResult.value.length > 0 && !shouldChunkFields) {
  const hasJsonTargets = await this.hasJsonTargetColumns(db, tableName, table, fieldIds);
  if (hasJsonTargets) {
    stepSpan?.setAttribute('step.sameTableCollapsedSkipped', true);
    stepSpan?.setAttribute('step.sameTableCollapsedSkipReason', 'json_target_column');
  }
  if (!hasJsonTargets) {
    const chunkedRecordIds = dirtyCount > SAME_TABLE_BATCH_CHUNK_TRIGGER
      ? await this.getDirtyRecordIdChunks(db, step.tableId)   // slices of 500
      : [];
    // SameTableBatchQueryBuilder.build per chunk with dirtyFilter on tmp_computed_dirty
  }
}
```
**Flow:** plan enters the updater → batches whose every field lacks cross-record propagation edges collapse to one level-ordered step (fields stay sorted by source level so the CTE chain reads dependencies first) → at execution, a collapsed step re-derives its original level structure (`collapsedBatchByStepKey`) and uses it ONLY if ALL of: (1) every field is `FieldType.formula()` (lookup/rollup/link bail out to plain lateral steps), (2) no target column is json/jsonb (probed live against `information_schema.columns`; formulas writing JSON break CTE reads), (3) dirty rows ≤ 1000 or chunked into ≤500-id slices (statement_timeout protection), (4) field count ≤16 or field-chunked (RETURNING merge path).
**Invariant:** collapsing is safe only for same-record dependencies — a lookup/rollup/link in the chain would read values computed by ANOTHER statement's write within the same UPDATE, which Postgres does not guarantee across CTEs; level order inside the flattened fieldIds preserves evaluation order, and any gate failure falls back to per-step execution rather than producing wrong values.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"chunks same-table CTE batch updates when dirty records exceed threshold"` (:2015); direct tests for the builder itself in `__tests__/SameTableBatch.spec.ts` + `query-builder/computed/SameTableBatchQueryBuilder.spec.ts` (see capsule `same-table-cte-formula-batch`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "optimizeSameTableBatches", limit: 5 });
// → ComputedFieldUpdater.optimizeSameTableBatches …/record/computed/ComputedFieldUpdater.ts 166-222
```

## Verdict
Adopt the collapse precondition set (pure same-record edges + formula-only + scalar column types) — each guard exists because a real porting bug class was hit upstream (cross-record reads inside one UPDATE; JSON columns unreadable mid-statement). Adopt trigger/chunk constants as tunable defaults, not magic. Adapt the information_schema probe to host catalog access. Omit the legacy `executeSameTableBatch`/`canBatchOptimize` stubs (:1469–1580, TODO path superseded by the collapsed-step flow). Coverage caveat: json-target skip asserted via span attribute in spec; no test pins an actual jsonb-target CTE failure.
