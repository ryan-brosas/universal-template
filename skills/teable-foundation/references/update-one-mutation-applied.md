<!-- capsule-v2 -->
# updateOne mutation-applied duality — when does an UPDATE return "nothing changed" instead of an error?

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does single-record update distinguish record-missing / value-unchanged from a real write, and what must be cleaned up on each path?

## Mutation-applied tri-state outcome
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:updateOne` (:2068–2235), `buildDistinctUserFieldWhere` (:123), snapshot session lifecycle :2148–2217.
**Signature:** `(context, table, recordId, mutateSpec, options?) => Promise<Result<RecordMutationResult, DomainError>>` where success is `{mutationApplied: boolean, changedFields?, computedChanges?, updateSnapshot?}`.
**Data Shape:** builder plan = `{setClauses, changedFieldIds, additionalStatements, impact:{impactHint, extraSeedRecords, exclusivityConstraints}, linkedRecordLocks}`.

### Decisive source
```ts
let updateQuery = db.updateTable(tableName).set(setClauses)
  .where(RECORD_ID_COLUMN, '=', recordIdStr);
if (distinctUserFieldWhere) updateQuery = updateQuery.where(distinctUserFieldWhere); // dedupe user snapshots
const updatedRow = changedFieldColumns.length > 0
  ? await updateQuery.returning(buildChangedFieldReturningSelects(changedFieldColumns)).executeTakeFirst()
  : (await updateQuery.executeTakeFirst(), undefined);
if (changedFieldColumns.length > 0 && !updatedRow) {
  await snapshotCaptureSession.abort();      // release undo capture BEFORE returning
  snapshotCaptureSession = undefined;
  return ok({ mutationApplied: false });     // not found OR values unchanged → Ok, not Err
}
```
Distinct-user-field guard keeps concurrent same-actor updates from fighting over one snapshot column:
```ts
safeTry<Expression<SqlBool> | undefined, DomainError>(function* () {
  // only fields whose column would receive DISTINCT-of-identical values need guarding
})
```

**Flow:** build plan via RecordUpdateBuilder → validate link exclusivity BEFORE persisting → open capture session → conditional UPDATE…RETURNING → zero rows ⇒ abort capture, return `mutationApplied:false` → else advisory locks → additional statements → finish capture → build update snapshot from undo rows (missing snapshot ⇒ loud Err) → run computed update by id → touch table meta.
**Invariant:** "no row updated" is SUCCESS data, never an exception — but the capture session MUST be aborted first or undo rows leak. Snapshot absence after a real update IS an error (`buildMissingSnapshotError`). Computed changes are extracted for THIS record only.
**Probe:** `record/repository/PostgresTableRecordRepository.update.spec.ts` + `.updateMany.pglite.spec.ts:506` 'does not update selector-matched rows when requested values are unchanged'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "updateOne mutationApplied snapshotCaptureSession abort distinctUserFieldWhere", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mutationApplied duality with explicit session abort, and the pre-persist exclusivity gate ordering (validate → persist). Adapt the distinct-guard to your audit columns. Omit i18n plumbing.
