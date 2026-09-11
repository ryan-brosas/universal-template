<!-- capsule-v2 -->
# Dirty-frontier BFS propagation — how do computed updates mark exactly the rows that must recompute, across link hops and generations?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a seed change-set expand through dependency edges into the full set of target records to recompute — without re-processing generations already enqueued and without UNION-branch duplication?

## Generation-keyed frontier loop over pg_temp.tmp_computed_dirty
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — `propagateDirtyRecords` (:2232–2397), per-edge select builder `buildPropagationSelect` (:2551–2774), dedup key `propagationQueryKey` (:2221–2222), generation cap `maxFrontierGenerations = Math.max(selectQueries.length, 1)` at :2291, termination `if (insertedRowCount === 0) break;` at :2382.
**Signature:** `propagateDirtyRecords(db: Kysely<DynamicDB>, edges: ReadonlyArray<ComputedDependencyEdge>, tableById: Map<string, Table>, context?: IExecutionContext): Promise<Result<DirtyPropagationStats, DomainError>>`.
**Data Shape:** dirty temp table `pg_temp.tmp_computed_dirty(table_id text, record_id text, generation integer default 0, primary key(table_id, record_id))` + frontier index `(generation, table_id, record_id)` (`resetDirtyTable` :1970–1996, `on commit drop`). Each edge select yields `(table_id lit, record_id ref)`, stamped with `generation = frontierGeneration + 1`.

### Decisive source
```ts
let maxFrontierGenerations = 1;
for (let frontierGeneration = 0; frontierGeneration < maxFrontierGenerations; frontierGeneration += 1) {
  // Multiple computed fields can share the same dirty-propagation path. Collapse
  // identical SELECTs for this frontier so we don't emit repeated UNION ALL branches.
  const preparedQueries = new Map<string, PreparedPropagationSelect>();
  // ... build+compile each edge select, key = `${compiled.sql}::${JSON.stringify(compiled.parameters)}`
  if (frontierGeneration === 0) {
    maxFrontierGenerations = Math.max(selectQueries.length, 1);
  }
  // ... single INSERT..SELECT over one unionAll chain:
  const nextGenerationQuery = db.selectFrom(unionQuery.as('propagated')).select([
    sql.ref(`propagated.${DIRTY_TABLE_ID_COL}`).as(DIRTY_TABLE_ID_COL),
    sql.ref(`propagated.${DIRTY_RECORD_ID_COL}`).as(DIRTY_RECORD_ID_COL),
    sql.lit(frontierGeneration + 1).as(DIRTY_GENERATION_COL),
  ]);
  // insert .. onConflict(table_id, record_id) doNothing
  if (insertedRowCount === 0) break;
}
```
**Flow:** seed records enter generation 0 → for each frontier generation N, every edge compiles ONE distinct-select reading ONLY `generation = N` rows (link-traversal selects in `buildDirtySelectQuery` filter `d.generation = dirtyGeneration`; all-target selects gate on the source table's frontier row via `buildGatedAllTargetSelect` :2523–2545 `limit(1)` EXISTS-style join) → identical compiled selects collapse via sql+params key → one `UNION ALL` feeds one `INSERT … ON CONFLICT DO NOTHING` stamping generation N+1 → loop ends when an insert round adds zero rows. Pass count is sized once from the first frontier's distinct-query count (a static depth bound), NOT run to fixpoint.
**Invariant:** every propagation select reads only its own generation slice — never the whole dirty table — so multi-hop chains advance one edge level per pass and rows are never re-seeded (PK conflict-do-nothing); the all-target fallback still respects the frontier (a gated EXISTS against generation N), so "refresh everything of this type" fires once per pass, not per seed row; identical edges share one UNION branch.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"deduplicates equivalent dirty propagation selects before building the batch SQL"` (:1177), `"gates all-target self-refresh propagation by the current dirty frontier"` (:1339), `"uses only the current dirty frontier on later propagation passes"` (:1631), `"propagates a multi-hop dirty frontier through successive generations"` (:1712).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "propagateDirtyRecords", limit: 5 });
// → ComputedFieldUpdater.propagateDirtyRecords …/record/computed/ComputedFieldUpdater.ts 2232-2397
```

## Verdict
Adopt the generation-keyed frontier temp table with PK-dedup inserts and per-generation read scoping — it is what makes bounded-depth cascade recomputes correct under concurrency; adopt the compile-once dedup key (sql+params string) for shared edges. Adapt table names/generation column to host schema; adapt the static pass bound (derived from first-pass query count) to your graph's known max depth or switch to a real fixpoint only if you also keep per-generation reads. Omit teable's OTel span plumbing. Coverage caveat: behavior pinned by SQL-shape assertions in the spec (pglite), not by concurrent-writer integration tests.
