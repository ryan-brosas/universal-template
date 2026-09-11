<!-- capsule-v2 -->
# Grid operation-queue batch save — how does a multi-row grid batch its cell edits into one save?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A grid lets the user edit many cells, add rows, and delete rows before pressing save — how do those queued operations become one atomic database write without duplicate statements or stale-row collisions?

## Closed operation union with compile-time exhaustiveness (`state/table-editor-operation-queue.types.ts`)
**Path/Symbol:** `apps/studio/state/table-editor-operation-queue.types.ts` : `QueuedOperationType` enum (:3-7), payload interfaces (:10-45), `QueuedOperation` union (:61), type-guard trio (:101-111).
**Signature:** `type QueuedOperation = EditCellContentOperation | AddRowOperation | DeleteRowOperation`.
**Data Shape:** every op carries `id`, `tableId`, `timestamp` plus a per-type payload; EDIT_CELL_CONTENT holds `rowIdentifiers` (PK values), `columnName`, `oldValue`/`newValue`, the full `Entity`, and `enumArrayColumns?`; ADD_ROW holds a client-generated `tempId` UUID (the row has no PK yet) plus `rowData`; DELETE_ROW holds `rowIdentifiers` plus the full `originalRow` for display/undo. A parallel `New*` union omits `id`/`timestamp` for not-yet-queued ops.

### Decisive source
```ts
export enum QueuedOperationType {
  EDIT_CELL_CONTENT = 'edit_cell_content',
  ADD_ROW = 'add_row',
  DELETE_ROW = 'delete_row',
}
```

**Flow:** grid interactions enqueue typed ops → the save mutation consumes the whole queue → SQL generation switches over the union.
**Invariant:** the op set is a closed discriminated union; the SQL generator's switch must be exhaustive at compile time (see the `never` check below) so adding a new op type breaks the build instead of silently dropping statements.
**Probe:** `apps/studio/data/table-rows/operation-queue-save-mutation.test.ts` (pure vitest, read whole) exercises the EDIT_CELL_CONTENT arm end-to-end.

## Batch assembly: fixed priority order, per-row edit coalescing, one transaction (`data/table-rows/operation-queue-save-mutation.ts`)
**Path/Symbol:** `apps/studio/data/table-rows/operation-queue-save-mutation.ts` : `getEditCellOperationRowKey` (:22-27), `getOperationSql` (:41-82), `sortOperations` (:85-95), `stripTrailingSemicolon` (:97-99), `getOperationSqlStatements` (:101-147), `saveOperationQueue` (:150-175), `useOperationQueueSaveMutation` (:179-217).
**Signature:** `getOperationSqlStatements(operations: readonly QueuedOperation[]): Array<SafeSqlFragment>`; `saveOperationQueue({ projectRef, connectionString, operations, roleImpersonationState }): Promise<{ result }>`.
**Data Shape:** statements are `SafeSqlFragment`s (pass-1 taint brand) — the queue never produces plain strings. Row-key = `tableId + JSON.stringify(sorted rowIdentifiers entries)`; the sort-by-key canonicalization makes `{a,b}` and `{b,a}` the same row, and JSON (not a naive join) keeps delimiter-colliding values distinct.

### Decisive source
```ts
function sortOperations(operations: readonly QueuedOperation[]): QueuedOperation[] {
  const operationOrder: Record<QueuedOperationType, number> = {
    [QueuedOperationType.DELETE_ROW]: 0,
    [QueuedOperationType.ADD_ROW]: 1,
    [QueuedOperationType.EDIT_CELL_CONTENT]: 2,
  }

  return [...operations].sort((a, b) => {
    return operationOrder[a.type] - operationOrder[b.type]
  })
}
```
```ts
    default: {
      // Error should never happen, but we'll handle it anyway. cast to never for exhaustive check.
      const _exhaustiveCheck: never = operation
      throw new Error(`Unknown operation: ${(_exhaustiveCheck as { type: string }).type}`)
    }
```
```ts
  const statements = getOperationSqlStatements(operations)

  const transactionSql = wrapWithTransaction(safeSql`${joinSqlFragments(statements, ';\n')};`)

  const sql = wrapWithRoleImpersonation(transactionSql, roleImpersonationState)
```

**Flow:** sort by type priority (DELETE 0 → ADD 1 → EDIT 2, so a delete+re-add of the same natural key cannot collide with a stale edit targeting the old row, and edits always target the final row set) → non-edit ops each become one statement (ADD_ROW strips internal `__tempId`/`idx` fields before SQL generation; DELETE_ROW builds a mock row `{idx: 0, ...rowIdentifiers}` to reuse the single-row builder) → edit ops group by canonical row key, each group collapsing into ONE `getTableRowUpdateSql` whose payload is `Object.fromEntries(group.map(...))` (last write wins per column) with the deduped union of enumArrayColumns → trailing semicolons stripped, statements joined and wrapped by pg-meta's `wrapWithTransaction` (`begin; … commit;`, Query.utils.ts:439-447) → impersonation wrap → pass-1's executeSql guard ladder.
**Invariant:** the whole grid save is ONE transaction — "If any operation fails, the entire transaction is rolled back" (doc comment) — and the batch is just another SafeSqlFragment, so every downstream guard (size cap, EXPLAIN preflight, impersonation line-rewind) applies unchanged. Exhaustiveness: the `never` default throws on an unknown op type rather than silently dropping it.
**Probe:** `operation-queue-save-mutation.test.ts` (65L, pure vitest, read whole) pins: same-row edits merge into one update (`where id = 1` appears exactly once, both columns in the SET list); different-row edits stay separate statements; identifier values that would collide under a naive delimiter join (`x|b:y` vs `y|b:z`) stay unmerged. Traced by hand against getOperationSqlStatements — vitest unexecutable in-lane (no node_modules in the read-only checkout), never claimed passing.

## Cross-table invalidation over the shared prefix key (`data/table-rows/keys.ts`)
**Path/Symbol:** `apps/studio/data/table-rows/keys.ts` : `tableRowKeys.tableRowsAndCount` (:11-13); `operation-queue-save-mutation.ts` : onSuccess (:193-206).
**Signature:** `tableRowsAndCount(projectRef?: string, tableId?: number): ['projects', string, 'table-rows', number]`.
**Data Shape:** a batch can touch many tables; onSuccess collects `affectedTableIds = [...new Set(operations.map(op => op.tableId))]` and invalidates each at the prefix key that covers BOTH the rows list and the count query.

### Decisive source
```ts
      // Collect all unique table IDs that were affected
      const affectedTableIds = [...new Set(operations.map((op) => op.tableId))]

      // Invalidate queries for all affected tables (both rows and count)
      await Promise.all(
        affectedTableIds.map((tableId) =>
          queryClient.invalidateQueries({
            queryKey: tableRowKeys.tableRowsAndCount(projectRef, tableId),
          })
        )
      )
```

**Flow:** save succeeds → dedup affected tables → parallel prefix-key invalidations → rows and counts for every touched table refetch.
**Invariant:** a batch mutation must invalidate by the SHARED prefix of every derived query it can change (rows + count), deduped per table — invalidating per-operation would repeat work; invalidating only the edited rows would leave counts stale.
**Probe:** direct read at the pin; the invalidation list has no dedicated test (consumer composition of the tested statements builder) — recorded absence.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin (every cited file additionally md5-verified byte-identical to its HEAD blob). Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getOperationSqlStatements saveOperationQueue sortOperations tableRowsAndCount wrapWithTransaction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the closed op union with a `never`-checked switch; fixed type-priority batch ordering (deletes → adds → edits); per-row edit coalescing via canonicalized identifier keys with last-write-wins column merge; internal-field stripping before SQL generation; one transaction for the whole batch routed through the existing guard ladder unchanged; deduped cross-table prefix-key invalidation. Adapt the op types, row-key canonicalization, and key prefix to your grid. Omit Supabase-product specifics: the exact PendingAddRow shape, sonner toast defaults, and the pgmq-adjacent queue state machine (UI-side reducer, not mined). Direct-test caveat: the pure statements-builder test was read whole and hand-traced; DB execution and vitest were not run in-lane — never claimed passing.
