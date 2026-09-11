<!-- capsule-v2 -->
# Orphan attachment GC — how do you delete files that no longer reference them, using a SQL HAVING trick instead of loading all references?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the cleanup job find fully-deleted references and reclaim storage without touching live attachments?

## HAVING COUNT(*) = COUNT(deleted) orphan scan
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/attachment-clean-up/attachment-clean-up.ts:AttachmentCleanUpProcessor.job` (14-93).
**Signature:** `job(job: Job): Promise<void>`; retention `NC_ATTACHMENT_RETENTION_DAYS` (default 10; 0 disables).
**Data Shape:** MetaTable.FILE_REFERENCES rows `{file_url, storage, deleted, updated_at}`; orphan = every row for a file_url has `deleted=true`.

### Decisive source
```ts
const orphanedFilesQueryBuilder = ncMeta
  .knexConnection(MetaTable.FILE_REFERENCES)
  .select('file_url')
  .max('updated_at', { as: 'last_updated_at' })
  .groupBy('file_url')
  .havingRaw('COUNT(*) = COUNT(CASE WHEN deleted THEN 1 END)');   // ALL refs soft-deleted

for (const file of orphanedFiles) {
  if (new Date(file.last_updated_at).getTime() > Date.now() - retentionDays * 86400e3) continue;
  const rootKey = await ncMeta.knexConnection(MetaTable.FILE_REFERENCES)
    .where('file_url', file.file_url).whereNotNull('storage').first();
  if (rootKey && file.storage !== storageAdapterName) continue;   // wrong adapter → skip
  await storageAdapter.fileDelete(path.join('nc', 'uploads', relativePath));
  for (const thumb of ['tiny.jpg', 'small.jpg', 'card_cover.jpg'])
    await storageAdapter.fileDelete(path.join('nc', 'thumbnails', relativePath, thumb));
  await ncMeta.knexConnection(MetaTable.FILE_REFERENCES).where('file_url', file.file_url).del();
}
```

**Flow:** group reference rows by file URL; the HAVING clause keeps only URLs where the count of rows equals the count of deleted-true rows (i.e., no live references). Respect retention on the newest update, verify storage-adapter ownership, then delete file + its three thumbnails and hard-delete the reference rows.
**Invariant:** never delete unless EVERY reference is tombstoned — one live row protects the file. Adapter check prevents cross-backend deletion when multiple adapters served over time. Deletion order matters: remove blobs first, meta rows last, so a crash mid-way leaves an orphan blob (harmless) rather than a dangling reference (would re-trigger deletion of a possibly re-uploaded file).
**Probe:** no unit test upstream. Source-grounded probe: `attachment-clean-up.ts:28-33` — havingRaw clause verbatim; `:83-86` — meta del strictly after both fileDelete loops.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AttachmentCleanUpProcessor FILE_REFERENCES havingRaw orphanedFiles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the count-equals-deleted-count HAVING pattern and delete-blobs-before-meta ordering; adapt table/column names, thumbnail set, and retention default to host; omit Local-vs-URL path derivation specifics. Coverage caveat: no in-repo tests; source-grounded.
