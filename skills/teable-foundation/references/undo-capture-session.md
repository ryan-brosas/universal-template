<!-- capsule-v2 -->
# UndoCaptureSession — trigger-based undo capture with local/global batch-id fallback

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a record mutation arm the undo-capture trigger, and how does it fall back from a local to a global batch id when the local one doesn't stick?

## Undo capture session
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresRecordMutationSnapshotCaptureService.ts` (whole file, 112-314).
**Signature:** `begin(traceContext, db, tableName): Promise<Result<IPostgresRecordMutationSnapshotCaptureSession, DomainError>>`; session `finish(): Promise<Result<UndoLogRow[], DomainError>>`, `abort(): Promise<void>`.
**Data Shape:** `ensureTable` installs the `__teable_undo_capture` trigger (via `ensureUndoCaptureInfrastructure`); `begin` mints a uuid batch id, reads the previous batch id, sets it (local first), verifies, and falls back to global if the local write didn't take. `finish` reads+clears undo log rows for the batch and restores the previous batch id.

### Decisive source
```ts
const batchId = generateUuid();
const previousBatchId = await getUndoCaptureBatchId(db);
let batchIdLocal = true;
let setResult = await setUndoCaptureBatchId(db, batchId, { local: true });
const verifiedBatchId = await getUndoCaptureBatchId(db);
if (setResult && verifiedBatchId !== batchId) {
  batchIdLocal = false;
  setResult = await setUndoCaptureBatchId(db, batchId, { local: false }); // global fallback
}
```

**Flow:** `begin` → ensureTable (install trigger; error if globals missing → `missing_globals`, else trigger-install failure) → mint batch id → save previous → set local → verify; if the local set didn't stick, retry global → verify again → return a session. `finish` → if not closed, `loadAndClearUndoLogRows(batchId)` filtered to this table, then restore previous batch id (or clear if none), mark closed. `abort` → load+clear rows, restore, closed. All wrapped in optional trace spans (best-effort, never affect queries).

**Invariant:** The batch id is the correlation key between the trigger-written undo rows and the app; local-then-global fallback handles environments where the local GUC doesn't propagate; `finish`/`abort` are idempotent via the `closed` flag and always restore the previous batch id.

**Probe:** `record/repository/PostgresRecordMutationSnapshotCaptureService.spec.ts` — pins begin/finish/abort and the local/global batch-id fallback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresRecordMutationSnapshotCaptureService begin setUndoCaptureBatchId batchIdLocal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the batch-id correlation, local-then-global fallback, and idempotent finish/abort with previous-id restore. Adapt the trigger/globals naming and migration requirement. Omit the shared `undoCapture.ts` internals (covered by the existing undo-capture-triggers capsule). Probes pinned to the real spec.
