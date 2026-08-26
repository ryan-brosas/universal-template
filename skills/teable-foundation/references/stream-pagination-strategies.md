<!-- capsule-v2 -->
# StreamPaginationStrategies — offset vs cursor stream pagination selection

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does `findStream` choose between offset and cursor pagination, and what are the two strategies' next-page contracts?

## Stream pagination strategies
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/CursorStreamPaginationStrategy.ts` (whole file) and `OffsetStreamPaginationStrategy.ts` (whole file).
**Signature:** each `implements ITableRecordStreamPaginationStrategy` with `accepts(pagination): boolean` and `next(input): ITableRecordStreamPaginationPage | null`.
**Data Shape:** `input = { pagination?, batchSize, yieldedCount, lastBatchCount?, lastCursor? }`. `next` returns `{type:'cursor', cursor, limit}` or `{type:'offset', offset, limit}` or `null` when exhausted.

### Decisive source
```ts
// Cursor accepts pagination with a 'cursor'; Offset accepts null or 'offset'
// (cursor strategy)
accepts(p) { return p != null && 'cursor' in p; }
next(input) {
  const maxLimit = input.pagination?.limit ?? Infinity;
  if (input.yieldedCount >= maxLimit) return null;
  const remaining = maxLimit - input.yieldedCount;
  const limit = Math.min(input.batchSize, remaining);
  if (limit <= 0) return null;
  return { type: 'cursor', cursor: input.lastCursor ?? input.pagination?.cursor, limit };
}
// (offset strategy) offset = startOffset + yieldedCount
```

**Flow:** `findStream` resolves the strategy via `streamPaginationStrategies.find(s => s.accepts(pagination)) ?? default(offset)`; each iteration calls `next`, dispatches to `findByOffsetPage`/`findByCursorPage`, yields records, and advances `yieldedCount`/`lastCursor` (cursor = last record's `__auto_number`). Both stop when `yieldedCount >= maxLimit` or `limit <= 0`.

**Invariant:** Cursor pagination is keyset on `__auto_number` and requires `orderBy __auto_number asc` only (validated in `findByCursorPage`); offset pagination is the default and the fallback; a page returning fewer records than requested ends the stream.

**Probe:** `record/repository/CursorStreamPaginationStrategy.spec.ts` and `OffsetStreamPaginationStrategy.spec.ts` — pin the accept/next contracts and limit math.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "CursorStreamPaginationStrategy OffsetStreamPaginationStrategy accepts next yieldedCount", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strategy-selection pattern and the shared limit/exhaustion math. Adapt the cursor-key (auto_number) and batch-size default. Omit nothing portable. Probes pinned to the real specs.
