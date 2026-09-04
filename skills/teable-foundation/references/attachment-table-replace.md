<!-- capsule-v2 -->
# AttachmentTableReplace — the attachments_table delete+insert replace protocol

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a record's attachment cell is replaced, what rows land in `attachments_table` and how is the replace made atomic per (table, record, field)?

## Attachment table replace mutations
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/attachments/attachmentTableMutations.ts` (whole file, 1-124).
**Signature:** `buildAttachmentTableReplaceQueries(db, {actorId, tableId, recordId, fieldId, value}): CompiledQuery[]`; `buildAttachmentTableBatchReplaceQueries(db, replacements): CompiledQuery[]`; `buildAttachmentTableInsertQuery(db, params): CompiledQuery | undefined`.
**Data Shape:** attachment cell value is an array (or single) of `{id, token, name?}`. Each row gets a fresh `generatePrefixedId('attt', 16)` row id, `attachment_id`, `token`, `name`, `table_id`, `record_id`, `field_id`, `created_by`. Rows missing `id` or `token` are dropped.

### Decisive source
```ts
// single replace: DELETE (table_id, record_id, field_id) then INSERT rows
const deleteQuery = db.deleteFrom('attachments_table')
  .where('table_id','=',params.tableId).where('record_id','=',params.recordId)
  .where('field_id','=',params.fieldId).compile();
const insertQuery = buildAttachmentTableInsertQuery(db, params);
return insertQuery ? [deleteQuery, insertQuery] : [deleteQuery];

// batch: ONE delete with tuple IN, deduped by (tableId,recordId,fieldId), then one multi-row insert
const tuples = [...uniqueDeleteTargets.values()].map(t => sql`(${t.tableId}, ${t.recordId}, ${t.fieldId})`);
const deleteQuery = sql`delete from attachments_table where (table_id, record_id, field_id) in (${sql.join(tuples)})`.compile(db);
```

**Flow:** normalize value to items → map to rows (drop id/token-less) → single: delete-by-triple then insert; batch: dedupe delete targets by triple key, emit one `(a,b,c) in (...)` delete + one multi-row insert. `CellValueMutateVisitor.visitSetAttachmentValue` either pushes these immediately (`additionalStatements`) or, when `deferAttachmentTableReplace`, accumulates `AttachmentTableReplaceInput[]` for a later batch call.

**Invariant:** Replace is delete-then-insert (never ON CONFLICT) so legacy tables without a unique constraint still work; the triple `(table_id, record_id, field_id)` is the replace key; a fresh prefixed row id is minted per row (not the attachment's own id).

**Probe:** `record/visitors/CellValueMutateVisitor.spec.ts` — `'can defer attachment table replacement for batch updates'` (:249) pins the defer path; `'clears non-link fields directly and records changed ids'` (:230) exercises the attachment clear path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildAttachmentTableReplaceQueries attachments_table delete insert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the delete-then-insert replace protocol, the prefixed row-id minting, and the batch tuple-IN dedupe. Adapt the `attt` prefix / 16-length. Omit nothing portable. Probes pinned to the real spec suite.
