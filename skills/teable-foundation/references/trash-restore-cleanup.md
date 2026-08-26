<!-- capsule-v2 -->
# Trash restore cleanup — after restoring records from trash, how does the code garbage-collect stale trash entries without breaking partial restores?

**Source:** teable AGPL `develop@06a4461e`. **Question:** record_trash/table_trash entries must be removed post-restore — what is the exact two-level cleanup and snapshot-parsing discipline?

## delete row entries → scan table snapshots → keep only tables whose OTHER records remain trashed
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `parseTrashedRecordIds(snapshot)` (:213–222), `asString` (:224), `cleanupRestoredRecordTrash(db, tableId, recordIds)` (:228–297); call site gated by option in `insertMany` :1690–1696 (`options?.cleanupTrashRecordIds?.length`). Companion capsules: `restore-identity-choreography`, `query-restore-batch-stamp`.
**Signature:** `cleanupRestoredRecordTrash(db, tableId, recordIds): Promise<void>`.

### Decisive source
```ts
await db.deleteFrom('record_trash')
  .where('table_id','=',tableId).where('record_id','in',restoredRecordIds).execute();   // row level
const candidateTrashItems = tableTrashItems.flatMap(item => {
  const id = asString(item.id); const snapshot = asString(item.snapshot);
  if (!id || !snapshot) return [];                       // malformed ⇒ skip, never throw
  const recordIds = parseTrashedRecordIds(snapshot);     // JSON.parse try/catch ⇒ []
  ...return item.recordIds.some(rid => restored.has(rid)) ? [{id, recordIds}] : [];
});
// stale = every record id in the snapshot is NO LONGER present in record_trash:
const staleTrashIds = candidateTrashItems
  .filter(item => item.recordIds.every(rid => !remainingRecordIdSet.has(rid)))
  .map(item => item.id);
if (staleTrashIds.length) await db.deleteFrom('table_trash').where('id','in',staleTrashIds).execute();
```

**Flow:** dedupe restored ids → delete their row-level entries → load ALL table-level trash items for this table whose JSON snapshots mention any restored id → re-query which of those record ids STILL have row entries → delete table entries ONLY where every listed record is now restored.
**Invariant:** A table_trash entry aggregates MANY records; deleting it because ONE member was restored would orphan the others' undo history — hence the "every member restored" predicate computed via a SECOND record_trash query rather than trusting the input list. Snapshot parsing degrades silently (`[]` on parse failure, non-string fields filtered) so one corrupt row cannot break a restore batch. The cleanup runs INSIDE the same tx as the restore inserts (:1690 inside insertMany's try block) — crash-consistent by construction.
**Probe:** deterministic grep :288–290 (stale predicate), :215–218 (parse guard).
**Coverage caveat:** no dedicated spec file pins this helper; exercised indirectly by restore flows — noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "cleanupRestoredRecordTrash table_trash record_trash staleTrashIds", limit: 5 });
```
## Verdict
Adopt for aggregated soft-trash designs: row entries deleted immediately, aggregate entries GC'd only when fully drained, corrupt snapshots skipped loudly-tolerant.
