<!-- capsule-v2 -->
# Computed-field backfill — how does teable backfill existing rows for a newly-added or changed computed field, choosing sync vs async by table size?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a computed field is added or its definition changes, how does teable recompute the existing rows without blocking a huge table or leaving a half-done backfill?

## Sync / async / hybrid backfill with outbox fallback
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldBackfillService.ts` — `ComputedFieldBackfillService.backfill` (143–174), `.backfillMany` (175–242), `.enqueue`/`.enqueueMany` (297–378), `.executeSync`/`.executeSyncMany` (379–570), `.needsBackfill` (571–598), `.collectBackfillFields` (599–817), `.shouldUseAsyncMode` (848–871), `.estimateTableRowCount` (872–917); config `FieldBackfillConfig`/`defaultFieldBackfillConfig` (65–115).
**Signature:** `backfill(table, changedFieldIds, executionContext?, options?): Promise<Result<...>>`; `backfillMany(...)`. Config carries `mode: 'sync'|'async'|'hybrid'`, `hybridThreshold`, and per-field limits.
**Data Shape:** backfill fields collected via `collectBackfillFields` (formula/link/lookup/rollup computed fields that `needsBackfill`). `shouldUseAsyncMode` returns the row-count estimate vs `hybridThreshold`, falling back to async when a UoW transaction is active and the estimate is unavailable.

### Decisive source
```ts
private async shouldUseAsyncMode(context, table): Promise<boolean> {
  if (this.config.mode === 'sync') return false;
  if (this.config.mode === 'async') return true;
  const rowCountEstimate = await this.estimateTableRowCount(context, table);
  if (rowCountEstimate !== undefined) return rowCountEstimate > this.config.hybridThreshold;
  const fallbackToAsync = hasUnitOfWorkTransaction(context);   // in a txn => async
  return fallbackToAsync;
}
// estimate: pg_class.reltuples vs pg_stat_all_tables.n_live_tup, GREATEST, ceil
SELECT GREATEST(c.reltuples, COALESCE(s.n_live_tup, 0), 0)::float8
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_all_tables s ON s.relid = c.oid
WHERE n.nspname = ${schema ?? 'public'} AND c.relname = ${tableName}
```
**Flow:** `backfill` collects the backfill fields, then decides sync vs async. Sync path runs the recompute in the current transaction (or a fresh one) and on failure falls back to enqueuing an outbox task (`enqueueAfterSyncFailure`). Async path enqueues outbox tasks (one per field, or one wide task for multi-field). Hybrid mode picks sync for small tables (≤ `hybridThreshold` rows) and async for large ones; when the row estimate is unavailable it defaults to async if inside a UoW transaction. `collectBackfillFields` handles the link-join column presence checks (oneMany/manyOne/oneOne/symmetric) so a backfill never queries a missing foreign-key column.
**Invariant:** a sync backfill failure must not be silently lost — it falls back to an outbox task (and if that also fails, the original sync error is returned); multi-field backfills enqueue separate tasks rather than one wide query; hybrid mode never blocks a large table synchronously; the row-count estimate degrades gracefully (unknown estimate → async-in-transaction) rather than guessing.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldBackfillService.spec.ts` — `"falls back to an outbox task when sync computed backfill fails"` (:375), `"returns original sync failure when outbox fallback also fails"` (:402), `"enqueues multi-field transaction backfills instead of building one wide sync query"` (:436), `"keeps hybrid field backfill synchronous for small tables"` (:465), `"enqueues hybrid field backfill for large tables"` (:485), `"enqueues hybrid transaction backfill when table row estimate is unavailable"` (:504).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedFieldBackfillService shouldUseAsyncMode collectBackfillFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sync/async/hybrid backfill decision keyed on a pg_class/pg_stat row estimate, the sync-failure→outbox fallback, per-field task enqueueing, and the foreign-key-column presence guards. Adapt the config surface, threshold, and field-type set. Omit teable's formula evaluation internals and the outbox worker mechanics (see `computed-update-outbox.md`).
