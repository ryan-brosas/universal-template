<!-- capsule-v2 -->
# BatchRecordUpdateBuilder — how do you turn N per-record mutation specs into ONE transposed batch-update payload with deduped, sorted locks?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** How does a batch of per-record updates get aggregated (per-record → per-column transpose, shared system columns, batched attachment replaces, deadlock-safe lock ordering) before any SQL exists?

## Batch data aggregation
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/update/BatchRecordUpdateBuilder.ts:buildBatchUpdateData` (:160–370).
**Signature:** `async buildBatchUpdateData({table, tableName, updates: ReadonlyArray<{recordId: RecordId; mutateSpec}>, context}): Promise<Result<BatchRecordUpdateDataResult, DomainError>>`.
**Data Shape:** `BatchRecordUpdateDataResult = { columnUpdateData: Map<columnName, Array<{recordId, value}>>; additionalStatements; linkedRecordLocks; impact: BatchRecordUpdateImpact; systemColumns: {lastModifiedTime, lastModifiedBy, versionIncrement:true}; recordIds }` — the transpose is EXPLICITLY documented as preparing for PostgreSQL's `(VALUES ...)` join pattern.

### Decisive source
```ts
// per-record visitor pass, then RAW set clauses (never compiled):
const raw = mutateVisitor.getSetClausesRaw();
for (const [columnName, value] of Object.entries(raw.setClauses)) {
  if (columnName === '__version') continue;        // version handled in BATCH SQL as t.__version + 1
  const resolvedValue = lastModifiedByJsonValue && lastModifiedByDbFieldNames.has(columnName)
    ? lastModifiedByJsonValue : value;             // context-built snapshot replaces per-row value
  recordSetClauses.set(columnName, resolvedValue);
}
// Step 2 transpose: Map<recordId, Map<col,val>> → Map<col, Array<{recordId, val}>>
```
LastModifiedBy handling: pre-scan all lastModifiedBy fields ONCE (:201–212), skipping generated ones; if any remain, build one JSON snapshot from context (`buildLastModifiedByJsonValue` :426–435) reused for every record. Attachment replaces are DEFERRED per record (`deferAttachmentTableReplace: true`) and flushed as ONE batched statement set via `buildAttachmentTableBatchReplaceQueries` (:296–304).
**Flow:** empty-batch early return with well-formed zero impact → precompute lastModifiedBy snapshot → per record: accept spec, harvest raw clauses + statements + link changes/locks → flush batched attachments → transpose → aggregate impact (value vs link field split, extra seeds) → dedupe+sort locks.
**Invariant:** `__version` must NEVER appear in per-record values — the SQL builder emits it as `t.__version + 1` so concurrent-safe monotonic bump happens once per row; carrying a literal version would pin stale values. Lock dedupe keeps FIRST occurrence but iterates/sorts by `foreignTableId:foreignRecordId` key so ALL transactions acquire locks in the same global order.
**Probe:** no dedicated unit spec for this builder; behavior pinned end-to-end via `PostgresTableRecordRepository.updateMany.pglite.spec.ts` and update.spec recording flows — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "BatchRecordUpdateBuilder buildBatchUpdateData transposeUpdateData deduplicateLinkedRecordLocks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the collect-raw-then-transpose architecture (visitor per record → per-column arrays → single VALUES-based UPDATE), the once-per-batch user snapshot, deferred+batched attachment replaces, and sorted lock dedupe for deadlock freedom. Adapt the CellValueMutateVisitor seam to your mutation representation. Omit teable-specific column naming (`__version`, `__last_modified_*`) where your schema differs — but keep the "system columns computed in SQL, never in payload" rule. Coverage caveat: pinned via repository-level suites only.
