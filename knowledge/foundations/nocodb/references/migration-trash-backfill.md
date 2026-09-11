<!-- capsule-v2 -->
# Trash backfill migration — resumable per-model scan reconstructing nc_trash rows from soft-delete markers

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How do you backfill a unified trash registry for soft-deletes that predate it — deriving delete events, deduping inserts, and resuming across restarts?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/nc_job_012_record_trash_backfill.ts:RecordTrashBackfillMigration` (job 69–196, processModel 198–373, markProcessed 426–434).

**Signature:** `job(): Promise<boolean>` (true = complete); `processModel(modelData): Promise<void>`; `markProcessed(modelId, completed, error?)`.

**Data Shape:** temp resume table `nc_temp_processed_record_trash_backfill(id, fk_model_id, completed, error)` — completed/failed rows both block re-selection; only stale in-flight rows (completed=false) are cleared at start. Derived event tuple: `(LMT, LMB)` DISTINCT over rows where the Deleted system column is true; resource_id = `` `${modelId}:${userId ?? ''}::${lmtIso}` ``; cleanup_due_at computed from the ORIGINAL deleted_at, not now().

### Decisive source
```ts
// page: one tuple per delete-event, ordered for stable offset paging
const tuples = await baseModel.dbDriver(baseModel.tnPath)
  .where(deletedColumn.column_name, true).distinct(...distinctCols)
  .orderBy(lmtCol.column_name, 'asc').limit(TUPLE_BATCH_SIZE).offset(offset);
// ONE bulk INSERT per page instead of 2N probe+insert round-trips;
// the natural unique key dedupes — matching the runtime listener's idempotent behavior
await ncMeta.knexConnection(MetaTable.TRASH).insert(rowsToInsert)
  .onConflict(['base_id', 'resource_type', 'resource_id']).ignore();
// dialect-dependent result: pg count vs mysql/sqlite id-array → telemetry upper bound
inserted += typeof result === 'number' ? result : Array.isArray(result) ? result.length : rowsToInsert.length;
```

**Flow:** ensure temp table → clear stale in-flight rows → count remaining models (mm=false ∧ meta-source ∨ local, minus already-processed) → PQueue loop at concurrency 10 (1 if ANY sqlite meta-source exists), self-throttling while `queue.size > concurrency*2`, re-querying batches of `concurrency*10` excluding in-flight ids → per model: skip if trash_disabled / non-meta / no Deleted+LMT columns / retention=0, else page DISTINCT tuples and bulk-insert trash rows → markProcessed(completed=true) in `finally`; model errors markProcessed(false, msg).

**Invariant:** retention must derive from the original LMT (`computeCleanupDueAt(deletedAtIso, days)`) so long-ago deletes purge on the next tick rather than earning fresh windows. The resume table treats COMPLETED and FAILED alike as visited (a poison model must not wedge the job) — only interrupted in-flight rows are retried. Concurrency collapses to 1 when any sqlite source exists (write-lock safety). Column lookup reads `nc_columns` directly with a bare SELECT — deliberately skipping Model.get/getColumns N+1s since only 3 system columns matter.

**Probe:** no unit test upstream. Source-grounded probe: header comment lines 16–41 (strategy + no-op conditions), `:71-85` (temp-table lifecycle + sentinel reset), `:119-125` (sqlite→serial), `:160-165` (queue-size throttle), `:308-313` (bulk-insert rationale comment verbatim), `:362-363` (page termination on short page).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "RecordTrashBackfillMigration markProcessed computeCleanupDueAt parseTrashRetentionEnv", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the temp-table resume ledger (failed = visited), distinct-tuple event reconstruction, and onConflict-ignore bulk inserts with original-date retention math; adapt table/column names to host; omit EE gating unless porting record trash. Coverage caveat: no in-repo unit tests; source-grounded.
