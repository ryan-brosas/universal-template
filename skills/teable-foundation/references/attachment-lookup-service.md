<!-- capsule-v2 -->
# AttachmentLookupService — meta-db attachment lookup with optional-column retry

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where do attachment lookups run (meta vs data db) and how do they survive missing optional metadata columns?

## Attachment lookup service
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresAttachmentLookupService.ts` (whole file, 52-229).
**Signature:** `listAttachmentsByTokens(tokens)` and `listAttachmentsByAttachmentIds(attachmentIds)`: `Promise<Result<AttachmentLookupRecord[], DomainError>>`.
**Data Shape:** `OPTIONAL_ATTACHMENT_COLUMNS = [{width},{height},{thumbnail_path→thumbnailPath}]`. Token lookup queries `attachments`; attachment-id lookup inner-joins `attachments_table` → `attachments` on token.

### Decisive source
```ts
// Attachment metadata lives in the META db, not the data-plane db.
// In BYODB spaces the data db is customer-owned and has no attachment tables.
constructor(@inject(v2RecordRepositoryPostgresTokens.metaDb) private readonly db) {}

// optional-column retry: a missing width/height/thumbnail column is dropped and re-queried
catch (error) {
  const missingColumn = extractMissingColumn(error); // /column "([^"]+)" does not exist/i
  if (missingColumn && OPTIONAL_ATTACHMENT_COLUMNS.some(c => c.dbColumn === missingColumn)
      && !excludedColumns.has(missingColumn)) {
    return this.queryAttachmentsByTokens(db, tokens, new Set([...excludedColumns, missingColumn]));
  }
  throw error;
}
```

**Flow:** dedupe+filter empty tokens/ids → query against the **meta db** (BYODB safety) → on a missing optional column error, retry with that column excluded (accumulating exclusions) → map rows to `AttachmentLookupRecord` (id/token/path/size/mimetype stringified/numbered, optional width/height/thumbnailPath parsed).

**Invariant:** Attachment metadata always lives in the meta db (never the customer data db); optional columns degrade gracefully (drop-and-retry) rather than failing the whole lookup; `parseThumbnailPath` returns undefined on non-string/empty/unparseable.

**Probe:** `record/repository/PostgresAttachmentLookupService.spec.ts` — pins the token/attachment-id lookups and the optional-column retry.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresAttachmentLookupService listAttachmentsByTokens metaDb OPTIONAL_ATTACHMENT_COLUMNS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the meta-db routing (BYODB safety) and the optional-column drop-and-retry. Adapt the table names and column set. Omit nothing portable. Probes pinned to the real spec.
