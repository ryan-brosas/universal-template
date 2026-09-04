<!-- capsule-v2 -->
# Dirty-set join placement — why the tmp_computed_dirty INNER JOIN must be applied BEFORE lateral joins

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** In an UPDATE…FROM over a small dirty subset of a huge table with per-row LATERAL subqueries, where must the subset filter sit so Postgres doesn't compute laterals for the whole table?

## Early dirty filter + optional record-id ANY() slice, mirrored into every host source
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.ts` — `withDirtyFilter` doc (:685–697), `$call(applyDirtyFilter)` ordering comment :836 ("Apply dirty filter BEFORE lateral joins"), builder `buildDirtyFilterJoin` (:875–904) with `__dirty` alias; id-slice predicate `buildDirtyRecordIdSlicePredicate` (:911–919, `${alias}.${recordIdColumn} = ANY(${recordIds}::text[])`, deduped non-empty ids :906–909); conditional-host twins `buildConditionalHostSource` (:921–946) / `buildConditionalHostKeySource` (:948–982) both inner-joining `__cond_dirty`.
**Signature:** `withDirtyFilter(config: IDirtyFilterConfig): this` where `IDirtyFilterConfig = {tableId, dirtyTableName?='tmp_computed_dirty', tableIdColumn?='table_id', recordIdColumn?='record_id', recordIds?: ReadonlyArray<string>}`.
**Data Shape:** main-table join `t.__id = __dirty.record_id AND __dirty.table_id = :tableId`; when a chunk slice is present an extra `__dirty.record_id = ANY(text[])` predicate restricts to that slice.

### Decisive source
```ts
/**
 * When set, the query will INNER JOIN with the dirty table immediately after
 * the main table (before any lateral joins), ensuring PostgreSQL can use the
 * small dirty table to drive indexed lookups on the main table.
 *
 * This is critical for UPDATE...FROM performance - without early filtering,
 * PostgreSQL may scan and compute lateral joins for all rows before filtering.
 */
const applyDirtyFilter = this.buildDirtyFilterJoin();
let query = this.db.selectFrom(`${tableName} as ${T}`)
  .select(() => selectColumns)
  .$call(applyDirtyFilter) // Apply dirty filter BEFORE lateral joins
  .$call(applyLateralJoins)
  .$call(applyConditionalJoins)
```
```ts
// The same dirty gate is repeated INSIDE set-based host sources so grouped
// aggregates only scan dirty hosts:
let query = this.db.selectFrom(`${hostTableName} as ${H}`)
  .innerJoin(`${dirtyTableName} as __cond_dirty`, (join) => join
    .onRef(`${H}.__id`, '=', `__cond_dirty.${recordIdColumn}`)
    .on(`__cond_dirty.${tableIdColumn}`, '=', dirtyConfig.tableId))
  .selectAll(H);
```
**Flow:** every generated UPDATE…FROM (and its embedded set-based aggregates) filters rows by joining the temp dirty table FIRST → for chunked steps the same builder receives `recordIds` and adds an `= ANY(text[])` predicate so each statement touches ≤500 ids within one TX → conditional/set-based subqueries re-apply the identical gate on their own host alias (`H`) rather than relying on the outer join.
**Invariant:** the dirty join is a semantic no-op (it selects exactly the rows the frontier marked) but a load-bearing PLANNING hint — moving it after the laterals changes the plan from index-driven nested loops to full scans with per-row lateral evaluation; the gate must be replicated in every derived table/host source or the aggregate silently computes over clean rows too. Slice predicates dedupe ids and drop empties so chunks never double-process.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.spec.ts` — `"scopes both ranked conditional rollup host sources to the dirty record slice"` (:2931), `"scopes set-based field-reference conditional rollup to dirty host rows"` (:2980); also pinned by `computed/__tests__/ComputedFieldUpdater.spec.ts` `"generates SQL for link computed updates with dirty propagation"` (:859).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildDirtyFilterJoin", limit: 5 });
// → ComputedTableRecordQueryBuilder.build Method …/query-builder/computed/ComputedTableRecordQueryBuilder.ts 773-867
```

## Verdict
Adopt "filter-first" as a hard rule when porting dirty-subset recompute onto UPDATE…FROM: outer join before laterals AND inside each host-derived table; adopt the ANY(text[]) slicing contract for timeout control without changing lock/TX scope. Adapt names/columns freely. Omit nothing else — this capsule is the whole seam. Coverage caveat: none material; SQL shape is directly snapshot/spec-tested at this pin.
