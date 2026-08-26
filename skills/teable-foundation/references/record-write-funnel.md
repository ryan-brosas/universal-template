<!-- capsule-v2 -->
# Record write funnel — how does the repository turn a domain mutation into SQL while keeping snapshot capture, link locks, and computed updates in a fixed order?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Every record mutation (insert/insertMany/updateOne/updateMany/deleteMany) repeats one choreography — what is the exact stage order a porter must preserve, and what breaks if stages are reordered?

## begin → mutate → locks → statements → computed → finish
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts` — `insert` (:1120–1348), `updateOne` (:2068–2235), `deleteMany` (:3049–3281); session type `IPostgresRecordMutationSnapshotCaptureSession` (`PostgresRecordMutationSnapshotCaptureService.ts`, already cited); error wrapper `wrapDatabaseError` from `../../shared/errors`. Tests: `PostgresTableRecordRepository.insert.pglite.spec.ts` 'returns stored insert snapshots from mutation capture' (:372), 'returns Err when insert snapshot capture does not record the inserted row' (:430); `PostgresTableRecordRepository.update.spec.ts` 'returns update snapshots captured from the undo log' (:777); `PostgresTableRecordRepository.delete.spec.ts` 'returns deleted record snapshots captured from the undo log' (:1118), 'returns Err when delete snapshot capture is incomplete' (:1185).
**Signature:** `insert(context, table, record, options?): Promise<Result<RecordMutationResult, DomainError>>`; all methods are `safeTry` generators returning neverthrow Results.

### Decisive source
```ts
let snapshotCaptureSession;
try {
  snapshotCaptureSession = yield* await this.recordMutationSnapshotCapture.begin(   // 1. ARM capture
    toRecordMutationSnapshotTraceContext(context), db, tableName);
  const insertedRow = /* 2. THE core DML (INSERT/UPDATE/DELETE with RETURNING) */;
  await acquireLinkedRecordLocks(db, baseId, linkedRecordLocks);                    // 3. advisory locks AFTER DML
  await RecordInsertBuilder.executeStatements(db, additionalStatements);            // 4. junction/FK/user side writes
  const computedResult = yield* await this.runComputedUpdate(...);                  // 5. inline computed plan+execute
  const mutationRows = yield* await snapshotCaptureSession.finish();                // 6. read undo-log rows INSIDE tx
  /* build RecordStoredSnapshot / RecordUpdateSnapshot from undo rows */
} catch (error) {
  await snapshotCaptureSession?.abort();                                            // abort on ANY failure
  return err(wrapDatabaseError(error, 'insert', { tableName }, context.$t));
}
```

**Flow:** arm a snapshot-capture session around the SAME db-or-tx handle BEFORE the core DML → execute the single core statement (optionally RETURNING changed fields) → acquire sorted linked-record advisory locks → run builder-emitted additional statements → run the computed-update step (mode-dependent; see seed capsule) → `finish()` reads the undo-log rows captured by DB triggers and reconstructs stored snapshots → any thrown error first calls `session.abort()` then wraps into a typed infrastructure DomainError.
**Invariant:** ORDER IS LOAD-BEARING: (1) capture must be armed before DML or the undo trigger rows for this tx are invisible to `finish()`; (2) `finish()` must run inside the same transaction — after commit the trigger rows' GUC-scoped batch id is gone and snapshots come back empty (test :430/:1185 pin exactly-count failures: expected N got M ⇒ err `record.snapshot.<op>_capture_incomplete`, never a silent partial result); (3) `abort()` MUST precede the `return err(...)` so the session releases its local state even when the caller later rolls back. A porter who moves snapshot reading after commit, or forgets abort-on-error, produces empty/poisoned undo snapshots.
**Probe:** `PostgresTableRecordRepository.insert.pglite.spec.ts` :372 (snapshots returned), :430 (incomplete ⇒ Err); `...update.spec.ts` :777; `...delete.spec.ts` :1118/:1185.
**Coverage:** fully indexed (file carries parse_partial flags only at lines beyond these ranges).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRecordRepository insert recordMutationSnapshotCapture finish abort", limit: 8 });
```
## Verdict
Adopt the six-stage funnel verbatim for any trigger-based audit/undo design: arm→DML→lock→side-writes→derived-work→finish-inside-tx, with abort-before-error-return. The Result-based error wrapping ladder is directly reusable.
