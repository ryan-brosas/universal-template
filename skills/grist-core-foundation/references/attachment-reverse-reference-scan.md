<!-- capsule-v2 -->
# Attachment usage reconciliation — how do you find which rows reference a value stored as JSON inside cells scattered across every table?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you compute reverse references and byte usage for attachment blobs whose pointers live in JSON arrays inside arbitrary user tables — without indexes and without scanning in application code?

## Schema-driven UNION ALL of json_each + SQL-side usage diffing
**Path/Symbol:** `app/server/lib/DocStorage.ts:scanAttachmentsForUsageChanges` (:1417–1450), `findAttachmentReferences` (:1457–1486), `getTotalAttachmentFileSizes` (:1380–1406), `removeUnusedAttachments` (:1511–1525), `getSoftDeletedAttachmentIds` (:1494–1505).
**Signature:** `async scanAttachmentsForUsageChanges(): Promise<{ used: boolean, id: number }[]>`; `async findAttachmentReferences(attId: number): Promise<SingleCell[]>`.
**Data Shape:** Attachments columns store JSON arrays of row-ids (`json_valid` guard required — legacy rows may hold invalid JSON per issue #1565); `_gristsys_Files(ident UNIQUE, data BLOB, storageId)` ↔ `_grist_Attachments(fileIdent, fileSize, timeDeleted)`.

### Decisive source
```sql
-- scanAttachmentsForUsageChanges: one query per Attachments column, UNION ALL'd,
-- flattened via json_each, then diffed against the metadata table IN SQL:
WITH all_attachment_ids(id) AS (
  SELECT json_each.value AS id
  FROM json_each(attachment_ids), (<all_columns_subquery>)
)
SELECT id, id IN all_attachment_ids AS used
FROM _grist_Attachments
WHERE used != (timeDeleted IS NULL);   -- only rows whose flag disagrees with reality

-- getTotalAttachmentFileSizes: MAX(LENGTH(blob)) reads the stored length,
-- NOT the blob body — the difference between ms and seconds on big files.
SELECT CASE WHEN files.storageId IS NOT NULL THEN MAX(meta.fileSize)
            ELSE MAX(LENGTH(files.data)) END AS len
FROM _gristsys_Files AS files JOIN _grist_Attachments AS meta
  ON meta.fileIdent = files.ident
WHERE meta.timeDeleted IS NULL
GROUP BY meta.fileIdent;   -- dedupe: identical content stored once, referenced N times
```

**Flow:** build one SELECT per column of type `Attachments` from `_docSchema` (dummy `SELECT '[0]'` first so the UNION never has an empty tail) → `UNION ALL` them (dupes fine, cheaper than DISTINCT) → `json_each` flattens id lists → compare against `_grist_Attachments.used` flag and return ONLY disagreeing rows → ActiveDoc flips `timeDeleted` accordingly → later, soft-deleted ids past `ATTACHMENTS_EXPIRY_DAYS` (7d — chosen so undo cannot resurrect after purge) are purged from `_gristsys_Files`, leaving remote stores to their own GC. For one attachment, `findAttachmentReferences` emits per-column joins against `json_each(t.col)` with `asLiteral()` quote-switching to inject table/column names as string literals.
**Invariant:** All heavy lifting stays in SQLite (json_each + UNION ALL), never a JS-side scan — but `json_valid(...)` guards are MANDATORY because malformed legacy cells crash json_each (issue #1565); usage truth lives in cell CONTENT while `timeDeleted` is just a cached flag — the WHERE clause diffs the two rather than trusting either; GROUP BY fileIdent prevents double-counting deduplicated blobs.
**Probe:** `test/server/lib/AttachmentFileManager.ts` (exercises attach/purge flows through these queries); DocStorage.js `.DeleteActions` covers action-history trimming nearby. No direct unit test isolates scanAttachmentsForUsageChanges — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "scanAttachmentsForUsageChanges findAttachmentReferences json_each attachments", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the schema-driven json_each/UNION ALL sweep for any "JSON pointer columns scattered across user tables" problem (attachments, mentions, tags). Adapt expiry windows and the two-table split (metadata vs blob storage) to host; keep MAX(LENGTH()) instead of reading blobs and keep the used-vs-flag DIFF shape so the reconciler stays idempotent. Omit remote-storageId branching if blobs are always inline.
