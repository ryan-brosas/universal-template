<!-- capsule-v2 -->
# Computed plan steps & propagation edges — how does planStage turn an affected-field set into ordered UPDATE steps, and which records does each edge refresh?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** After the topo-sort, how are propagation edges deduplicated/merged, when is filtering "precise" vs whole-table, and which steps survive on DELETE?

## Step-building continuation of ComputedUpdatePlanner.planStage
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedUpdatePlanner.ts` — INSERT conditional seeding (:613–660), context-free formula inclusion (:663–681), fallback formula-edge fixed point (:684–733), oneMany insert filter (:741–748, helper :1281–1330), cycle skip (:762–862), `buildPropagationEdges` (:1616–1911), `buildSteps` (:1521–1553), `collectDeleteSeedTableRetainedFieldIds` (:1557–1587), `buildSameTableBatches` (:1930–2010).
**Signature:** `buildPropagationEdges(edges, fieldsById, computedFieldIds, levels, symmetricLinkEdges, seedTableId, extraSeedTableIds, changedFieldIds, changeType, hasSeedRecords, beforeImageRecords): Result<ComputedDependencyEdge[], DomainError>`; `buildSteps(ordered, levels, fieldsById): Result<UpdateStep[], DomainError>`; `buildSameTableBatches(steps, edges): SameTableBatch[]`.
**Data Shape:** Propagation edge = `{from/toFieldId, from/toTableId, linkFieldId?, propagationMode: 'linkTraversal'|'conditionalFiltered'|'allTargetRecords', filterCondition?: {foreignTableId, filterDto, includeBeforeImage?}, allTargetRecordsReasons?, order}`. Steps group `{tableId, level, fieldIds[]}` sorted by level then tableId.

### Decisive source
```ts
// Edge merge key: mode + tables + self-refresh marker + link field + filter identity.
// Duplicate seams (many fields reached via the same link/filter) MERGE target lists
// instead of emitting one edge per target — one traversal refreshes many fields.
const propagationEdgeKey = (edge: ComputedDependencyEdge): string => {
  const propagationMode =
    edge.propagationMode ?? (edge.linkFieldId ? 'linkTraversal' : 'allTargetRecords');
  const isSelfRefresh =
    propagationMode === 'allTargetRecords' &&
    edge.fromTableId.equals(edge.toTableId) &&
    edge.fromFieldId.equals(edge.toFieldId);
  return [
    propagationMode,
    edge.fromTableId.toString(),
    edge.toTableId.toString(),
    isSelfRefresh ? 'self' : 'gated',
    edge.linkFieldId?.toString() ?? '',
    filterConditionKey(edge),
  ].join('|');
};
```

**Flow:** (1) INSERT-only: conditionalRollup/conditionalLookup fields invisible to same-record scanning get seeded so new rows compute stored reads (:613–660). (2) Context-free formulas (`dependencies().length === 0` AND no referenced ids) join every non-delete plan. (3) Fallback fixed point: while schema conversion hides reference rows, same-table formulas reachable from seeds synthesize `same_record` edges until closure. (4) INSERT drops un-set oneMany links whose FK lives in the foreign table (null→null churn) but keeps explicitly-set values AND symmetric twins of explicit links. (5) Cycle: topo leftover → DFS finds one cycle → `cyclePolicy:'skip'` removes cycle participants and retries sort, else `domainError.conflict`. (6) Propagation-mode ladder for conditional fields: missing filterDto ⇒ `allTargetRecords('conditional_missing_filter')`; same-table DELETE ⇒ `allTargetRecords('conditional_delete')`; needs-old-match-tracking (delete / filter fields outside source∪target / update touching filter fields) WITH before-images ⇒ `conditionalFiltered{includeBeforeImage:true}`; without ⇒ conservative `allTargetRecords` with resolved reason; otherwise precise `conditionalFiltered`. (7) Filtered lookup/rollup stay `linkTraversal` even when filter fields changed (relation still bounds the blast radius) EXCEPT DELETE where `canTraverseFilteredDeleteWithoutSourceRecord` (manyMany/manyOne/oneOne, or oneWay oneMany) fails ⇒ `allTargetRecords('filtered_lookup_delete_requires_source_record')`. (8) Symmetric links: `linkTraversal` when seed records exist else `allTargetRecords('symmetric_no_seed_records')`. (9) DELETE prunes seed-table steps unless an `allTargetRecords` edge targets the seed table; retained field set expands through same-table chains (`collectDeleteSeedTableRetainedFieldIds`). (10) `buildSameTableBatches` merges consecutive same-table steps with NO cross-record dependency into CTE batches.
**Invariant:** The merge key MUST include the filter condition identity and the self-refresh marker — merging two different filters into one edge silently widens refreshed rows; conversely identical filters MUST merge or one link change fans out N duplicate traversals. Steps within a batch must never depend cross-record on each other (batch executes as ONE statement).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedUpdatePlanner.spec.ts` (describes at :1016 conditionalFiltered, :1624 conditionalLookup, :1776 filtered lookup/rollup, :2088 no-seed schema update, :2182 symmetric pruning, :2241 delete seed-table retention); `__tests__/SameTableBatch.spec.ts` (batching splits on cross-record deps; orders by minLevel).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildPropagationEdges buildSameTableBatches collectDeleteSeedTableRetainedFieldIds", limit: 10 });
```

## Verdict
Adopt the propagation-mode decision ladder (precise-filter vs before-image vs whole-table), edge merge-key discipline, oneMany-insert pruning, delete seed-step retention, and CTE same-table batching; adapt mode/reason enums and FieldMeta shapes to host; omit teable's conditional-field type names if host lacks them (the ladder structure ports regardless).
