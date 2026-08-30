<!-- capsule-v2 -->
# Distinct-host-key unchunked probe — when large dirty sets may skip record-id chunking for conditional aggregates

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Record-id chunking protects statement_timeout but serializes work — under what measured conditions can a big conditional-lookup/rollup step execute as ONE unchunked statement safely?

## Cardinality-bounded host keys decide; builder reports eligibility, updater confirms with SQL
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — constants `DISTINCT_HOST_KEY_UNCHUNK_MAX_DIRTY_RECORDS = 50_000` / `DISTINCT_HOST_KEY_UNCHUNK_MAX_KEYS = 5_000` (:80–81); probe window `canProbeDistinctHostKeyAggregation = dirtyCount > SAME_TABLE_BATCH_CHUNK_TRIGGER && dirtyCount <= 50_000 && every field conditionalLookup|conditionalRollup` (:1175–1185); per-chunk builder construction reading `builder.canExecuteUnchunkedDirtySet()` + `unchunkedHostKeyColumns()` (:1187–1227); confirmation query `hasBoundedDistinctHostKeys` (:1641–1679, `select count(*) from (select distinct h.<col> … join dirty … limit MAX_KEYS+1)`, any column over the cap ⇒ false).
**Signature (builder side):** `canExecuteUnchunkedDirtySet(): boolean`; `unchunkedHostKeyColumns(): ReadonlyArray<string>` (`ComputedTableRecordQueryBuilder.ts` :699–705); columns populated only when EVERY conditional subquery took `joinMode:'hostKey'` (:1678–1687).
**Data Shape:** eligibility = all-lateral-group output is keyed by scalar text host keys (`__host_key`), i.e. singleLineText↔singleLineText field-reference groups only.

### Decisive source
```ts
if (queryPlans) {
  canExecuteUnchunked = yield* await this.hasBoundedDistinctHostKeys(
    db, tableName, step.tableId.toString(), [...hostKeyColumns]);
}
// hasBoundedDistinctHostKeys, per column:
const query = sql`
  select count(*)::integer as "count" from (
    select distinct ${hostKeyRef} as "__key"
    from ${sql.raw(toQualifiedIdentifierLiteral(tableName))} as "h"
    inner join ${sql.table(DIRTY_TABLE)} as "d"
      on "d"."record_id" = "h"."__id"
    where "d"."table_id" = ${tableId}
    limit ${DISTINCT_HOST_KEY_UNCHUNK_MAX_KEYS + 1}
  ) as "__keys"`.compile(db);
// count > DISTINCT_HOST_KEY_UNCHUNK_MAX_KEYS → ok(false)
```
**Flow:** dirty rows ≤1000 → never chunked anyway → between 1000 and 50,000 AND every field is a conditional aggregate whose group joined via scalar host key → build unchunked plans, collect the union of host-key columns, and run one bounded COUNT(DISTINCT) per column against the actual dirty set → all within 5,000 distinct values ⇒ execute ONE statement (the grouped aggregate fans out internally); otherwise fall through to 500-id record-id chunks. The two-level check matters because the static type gate says nothing about real cardinality.
**Invariant:** the probe's cost is capped (`limit MAX_KEYS+1`) so deciding costs O(small) regardless of data size; unchunking is allowed ONLY where the join mode already guarantees one grouped row per distinct host key — applying it to lateral-shaped groups would multiply per-row subexecutions instead of collapsing them. Failure of the probe degrades to chunking (safe direction), never to skipping.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"executes distinct-host-key conditional aggregates without record-id chunks"` (:2187); builder-side eligibility pinned by `"conditional rollups with residual field-ref filters use set-based host joins"` family in `ComputedTableRecordQueryBuilder.spec.ts` (:2680+).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "hasBoundedDistinctHostKeys", limit: 5 });
// → ComputedFieldUpdater.hasBoundedDistinctHostKeys …/record/computed/ComputedFieldUpdater.ts 1641-1679
```

## Verdict
Adopt the measure-don't-assume pattern: static shape gate → cheap bounded-cardinality SQL probe → choose chunked vs unchunked execution, defaulting to chunked. Adapt thresholds to your statement_timeout budget. Omit teable's span attributes. Coverage caveat: the happy-path spec asserts the generated SQL; the >5,000-distinct fallback is enforced by the limit arithmetic rather than its own dedicated test.
