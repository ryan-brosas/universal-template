<!-- capsule-v2 -->
# DB-trigger undo capture — how do you record row-level before/after images for every write path, including raw SQL you don't route through your repository?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How can a transactional undo log capture INSERT/UPDATE/DELETE images without instrumenting every write site — and fail open (not break the write) when infrastructure is missing?

## Trigger-captured undo log with savepoint-guarded self-install
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/shared/undoCapture.ts` (whole file, 328L): infra check `ensureUndoCaptureInfrastructure` (217–268), per-table trigger install `createTableTrigger` (204–215), savepoint wrapper `runWithSavepoint` (92–112), batch-id config `setUndoCaptureBatchId`/`getUndoCaptureBatchId`/`restoreUndoCaptureBatchId`/`clearUndoCaptureBatchId` (270–310), drain `loadAndClearUndoLogRows` (312–328), cache `undoCaptureCaches: WeakMap<object, UndoCaptureCache>` (27–58); global SQL objects in `shared/undoCaptureGlobalsSql.ts`; installer `shared/installUndoCaptureGlobals.ts`.
**Signature:** `ensureUndoCaptureInfrastructure(rootDb: object, db: Kysely<DB>|Transaction<DB>, tableRef, tableKey): Promise<'ready'|'missing_globals'|'trigger_install_failed'>`; `loadAndClearUndoLogRows(db, batchId): Promise<UndoLogRow[]>`.
**Data Shape:** `__undo_log` rows `{id, batch_id, operation: 'INSERT'|'UPDATE'|'DELETE', table_name, record_id, old_row jsonb, new_row jsonb}` written by the plpgsql function `__teable_capture_undo_row()` attached via trigger `__teable_undo_capture`; batch scoping uses the session GUC `teable.undo_batch_id` (`set_config(..., is_local = inTransaction)`).

### Decisive source
```ts
const runWithSavepoint = async (db, work) => {
  const savepointName = nextSavepointName(); // time+random, quote-escaped
  try {
    await sql.raw(`SAVEPOINT ${savepointIdentifier}`).execute(db);
    await work();
    await sql.raw(`RELEASE SAVEPOINT ${savepointIdentifier}`).execute(db);
    return true;
  } catch {
    try { // never let cleanup kill the caller's transaction
      await sql.raw(`ROLLBACK TO SAVEPOINT ${savepointIdentifier}`).execute(db);
      await sql.raw(`RELEASE SAVEPOINT ${savepointIdentifier}`).execute(db);
    } catch { /* Ignore cleanup failures to keep the caller's transaction alive. */ }
    return false;
  }
};
// drain = atomic claim: DELETE ... RETURNING ordered by id
WITH deleted AS (
  DELETE FROM "__undo_log" WHERE "batch_id" = ${batchId}
  RETURNING "id","operation","table_name","record_id","old_row","new_row")
SELECT ... FROM deleted ORDER BY deleted."id" ASC
```

**Flow:** before writing to a dynamic table, ensure infra: WeakMap cache keyed on the ROOT db object short-circuits repeat checks → verify globals exist (table + `new_row` column + function, via information_schema/pg_proc) → verify this table's trigger exists **and points at THIS schema's function** (pg_trigger join pg_proc; restored-from-backup triggers pointing elsewhere are treated as stale and reinstalled) → install missing triggers inside a SAVEPOINT so a failure rolls back only the DDL attempt → set the batch GUC → run writes → drain with DELETE…RETURNING for exactly this batch. Statuses: `'missing_globals'` / `'trigger_install_failed'` mean undo is unavailable but THE WRITE PROCEEDS.
**Invariant:** capture must be transparent and non-blocking: any infra failure degrades to no-undo, never a failed user write; transaction-local installs are NOT cached (`if (!isTransactionDb(db)) cache.add(...)` — a rolled-back CREATE TRIGGER must not poison the cache); drains are single-consumer atomic (delete-returning) so concurrent readers can't double-replay.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/shared/undoCapture.spec.ts::"accepts an existing undo trigger only when it targets the current schema function"` (:102), `::"reinstalls stale restored triggers that point outside the current schema"` (:128), `::"checks restored triggers through the scoped transaction connection"` (:154).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "ensureUndoCaptureInfrastructure loadAndClearUndoLogRows runWithSavepoint",
  limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt DB-trigger undo capture for any system where writes arrive through multiple paths (ORM + raw SQL + bulk tools): one trigger captures everything, app code only sets/drains batch ids; adopt the savepoint-guarded best-effort install and WeakMap-per-root-connection caching. Adapt the function/trigger/GUC names, payload columns, and retention to host. Omit teable's v2 undo command replay layer if you already have an application-level undo stack (pair this with the undo-redo-stack capsule). Caveat: parse_partial flagged at lines 115/128/142/158 (SQL template literals) — excerpts verified against raw source.
