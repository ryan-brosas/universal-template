<!-- capsule-v2 -->
# Auto-number cursor paging — how do you page an UPDATE...FROM SELECT over huge tables without keyset drift?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the correct cursor strategy when record-id IN-lists are too large?

## AutoNumberCursorStrategy
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-pagination.strategy.ts:AutoNumberCursorStrategy.run` (:67–109; twin `RecordIdBatchStrategy` :36–65).
**Signature:** `run(context, onBatch): Promise<void>` with context `{baseQueryBuilder, orderColumn, cursorBatchSize, updateRecords(qb, opts?), ...}`.

### Decisive source
```ts
const sortedRows = rows.slice().sort((a, b) => {                       // :89–94
  const left = (a[AUTO_NUMBER_FIELD_NAME] as number) ?? 0;
  const right = (b[AUTO_NUMBER_FIELD_NAME] as number) ?? 0;
  if (left === right) return 0;
  return left > right ? 1 : -1;
});
await onBatch(sortedRows);                                             // :96 AFTER sort
...
if (lastCursor != null) { cursor = lastCursor; }                       // :100–102
if (sortedRows.length < context.cursorBatchSize) { break; }            // :104–106
```

**Flow:** strategy table `[RecordIdBatchStrategy, AutoNumberCursorStrategy]`; selection = first canHandle, last-as-default (`?? strategies[len-1]`, evaluator :403–408). RecordIdBatch handles ≤10k ids (chunked whereIn + restrictRecordIds); cursor strategy = fallback (canHandle always true). Cursor loop clones the BASE builder each round, orders by auto-number ASC, limits batch; rows RE-SORTED in JS before handling because UPDATE...FROM SELECT output order isn't guaranteed even with ORDER BY on all engines; cursor advances ONLY from the re-sorted tail and only when non-null; termination = short page.
**Invariant:** The in-memory re-sort before onBatch is load-bearing — publishing ops from unsorted DB output could advance the cursor past unprocessed rows. Null cursors never advance (rows without auto-number can't be paged past → they'd loop forever if used as cursor).
**Probe:** needles verified at this pin (:89 sort-before-handle, :104 short-page break); exercised via `packages/v2/e2e/src/computed-high-cardinality-link.e2e.spec.ts` (>10k-record path forces cursor strategy); graph retrieval resolves :67–109.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "AutoNumberCursorStrategy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt clone-per-page + JS re-sort + null-cursor guard; adapt AUTO_NUMBER_FIELD_NAME to your ordering column; omit the strategy-object pattern for a plain branch if you prefer.
