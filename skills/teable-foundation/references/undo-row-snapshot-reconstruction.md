<!-- capsule-v2 -->
# Undo-row snapshot reconstruction — how do DB-trigger audit rows become typed insert/update/delete snapshots, and which row wins when several exist?

## group by record_id → walk NEWEST→OLDEST → first parseable new_row (current) or first DELETE old_row (deleted) → version-missing = hard error
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `groupUndoLogRowsByRecordId(rows, recordIds?)` (:660–681), `toStoredRowObject(value)` (:641–658), `buildStoredRecordSnapshotFromRow(table,row)` (:567–626), `buildStoredRecordSnapshotsFromCurrentUndoRows` (:683–708), `buildStoredRecordSnapshotsFromDeletedUndoRows` (:710–742), `buildRecordUpdateSnapshotFromUndoRows` (:744–798, version guard :783–790), `buildMissingSnapshotError` (:800–809).
**Signature:** inputs `UndoLogRow {record_id, operation: 'INSERT'|'UPDATE'|'DELETE', old_row, new_row}` (from `shared/undoCapture`, cited by undo-capture-session).

### Decisive source
```ts
// current state: newest-first, FIRST parseable new_row wins:
for (let index = recordRows.length - 1; index >= 0; index -= 1) {
  const currentRow = toStoredRowObject(recordRows[index]?.new_row);
  if (currentRow) { currentRows.push(currentRow); break; }
}
// deleted state: first row that IS a DELETE (or old-only) walking newest-first:
if (recordRow?.operation !== 'DELETE' && !(recordRow?.old_row != null && recordRow?.new_row == null)) continue;
// update pair: previous = updateRows[0].old_row ; current = LAST parseable new_row
const oldVersion = Number(previousRow['__version']); const newVersion = Number(currentRow['__version']);
if (oldVersion == null || newVersion == null)
  return err(domainError.infrastructure({ code: 'record.snapshot.update_version_missing', ... }));
```

**Flow:** group trigger rows per record (optional id filter) → snapshots build from the row objects' physical db columns mapped through table field metadata (missing columns skipped, orders from `__row_*` when finite) → current-snapshots take the freshest parseable after-image; deleted-snapshots require an explicit DELETE-shaped row's before-image; update-pairs pin previous=FIRST update's old_row vs current=LAST parseable new_row.
**Invariant:** FOUR traps: (1) Reverse iteration with FIRST-match semantics implements "latest wins with fallback" — a corrupt newest row degrades to the previous one rather than failing the whole mutation. (2) Update snapshots HARD-FAIL on missing `__version` in either image (`update_version_missing`) because versions drive optimistic concurrency; other snapshot types tolerate missing fields silently. (3) `toStoredRowObject` accepts object OR JSON-string cell values — driver-dependent encoding must not break reconstruction. (4) Expected-vs-actual count mismatches become typed errors via buildMissingSnapshotError (`record.snapshot.<op>_capture_incomplete`), never silent partials.
**Probe:** update.spec.ts 'uses the last UPDATE undo row as the update snapshot after-image' (:855), 'returns Err when update snapshot capture is missing version metadata' (:932); delete.spec.ts :1118/:1185.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildStoredRecordSnapshotsFromCurrentUndoRows buildRecordUpdateSnapshotFromUndoRows UndoLogRow", limit: 8 });
```
## Verdict
Adopt for trigger-based audit designs: newest-first first-parseable-walk reconstruction, operation-shape predicates, hard version contract on update pairs.
