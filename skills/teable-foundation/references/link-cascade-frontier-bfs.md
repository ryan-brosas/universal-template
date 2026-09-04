<!-- capsule-v2 -->
# Link-cascade frontier BFS — how do you propagate a record-id set across link junction tables without recursive CTEs or full scans?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the correct iterative algorithm for expanding seeds through FK junction tables across arbitrary link graphs?

## LinkCascadeResolver.resolve
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/link-cascade-resolver.ts:LinkCascadeResolver.resolve` (:56–152; helpers to :252).
**Signature:** `resolve({ explicitSeeds: [{tableId, recordIds}], allTableSeeds: [{tableId, dbTableName}], edges: [{foreignTableId, hostTableId, fkTableName, selfKeyName, foreignKeyName}] }): Promise<Array<{tableId, recordId}>>`.

### Decisive source
```ts
const IN_CHUNK = 500;                                                    // :53
// :100–117 frontier loop
while (queue.length) {
  const { tableId, ids, all } = queue.shift()!;
  const edgesFromTable = edgeBySrc.get(tableId);
  if (!edgesFromTable?.length) continue;
  const frontierIds = all ? [] : Array.from(ids ?? []).filter(Boolean);
  ...
  const rows = all ? await this.fetchEdgeTargetsFromAll(edge)
                   : await this.fetchEdgeTargetsBatched(edge, frontierIds);
// :111–113 destination saturation short-circuit
const dstVisited = visited.get(edge.hostTableId);
if (dstVisited === ALL_RECORDS) continue; // already fully included
```

**Flow:** visited-map holds either a Set or the module-local `ALL_RECORDS` Symbol (:50–51); explicit seeds enqueue their exact ids, all-table seeds enqueue `{all:true}` WITHOUT materializing (:92–98); each hop queries only the junction table filtered by the CURRENT frontier (`where srcCol in (...)` chunked at 500 via lodash `chunk` + `Promise.all` flatMap, :215–225) or unbounded `SELECT DISTINCT` when `all` (:227–240); only newly-discovered ids are enqueued (:127–138); ALL_RECORDS destinations are skipped entirely. Identical `ALL_RECORDS` Symbol duplicated in the collector (:71) — the resolver RETURNS only concrete pairs (:142–151) and the CALLER re-applies its own sentinel for all-seeded tables (collector :458–461).
**Invariant:** Frontier-only querying keeps every statement an indexed junction lookup — never join the full edge table. Ids are cast `::text` in SQL (:202) so numeric/text `__id` types compare uniformly in Sets. The `all` flag travels per-queue-entry; once a table saturates to ALL_RECORDS it never re-enqueues (monotone growth).
**Probe:** exercised via `packages/v2/e2e/src/computed-high-cardinality-link.e2e.spec.ts` (deep multi-hop cascades); graph retrieval `LinkCascadeResolver.resolve` resolves :64–152 line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "LinkCascadeResolver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the frontier-BFS + saturation short-circuit + 500-id chunking; adapt identifier quoting (`formatQualifiedName` splits schema.table and double-quotes parts, :246–251) to your catalog; omit Postgres-specific `$n` placeholder style only if your driver differs. No dedicated unit spec — caveat noted.
