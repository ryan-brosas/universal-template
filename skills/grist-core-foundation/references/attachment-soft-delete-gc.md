<!-- capsule-v2 -->
# Attachment Soft-Delete & GC — how do you reconcile which attachments are still referenced and reclaim the rest without blocking edits or losing undo?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the two-phase (soft-delete → hard-delete) reconciliation that scans attachment usage, marks unreferenced ones, lets undo resurrect them, and finally purges expired ones — and where does it run?

## scan → soft-delete (undoable) → expired hard-delete ladder
**Path/Symbol:** `app/server/lib/ActiveDoc.ts` — `updateUsedAttachmentsIfNeeded` (:2161–2173), `removeUnusedAttachments` (:2185–2206); storage side `DocStorage.scanAttachmentsForUsageChanges``, `getSoftDeletedAttachmentIds`, `removeUnusedAttachments` (in `app/server/lib/DocStorage.ts`); wiring: hourly `Interval` (:400–403) plus shutdown-time invocation (:2645).
**Signature:** `updateUsedAttachmentsIfNeeded(): Promise<boolean>`; `removeUnusedAttachments(expiredOnly: boolean, options?: UpdateUsageOptions): Promise<void>`.
**Data Shape:** usage scan returns `{id, used}[]`; soft-delete writes `BulkUpdateRecord("_grist_Attachments", rowIds, { timeDeleted: used ? null : now })`; hard-delete uses `BulkRemoveRecord` then `docStorage.removeUnusedAttachments()`.

### Decisive source
```ts
public async updateUsedAttachmentsIfNeeded() {
  const changes = await this.docStorage.scanAttachmentsForUsageChanges();
  if (!changes.length) { return false; }
  const rowIds = changes.map(r => r.id);
  const now = Date.now() / 1000;
  const timeDeleted = changes.map(r => r.used ? null : now);
  const action: BulkUpdateRecord = ["BulkUpdateRecord", "_grist_Attachments", rowIds, { timeDeleted }];
  // Don't use applyUserActions which may block the update action in delete-only mode
  await this._applyUserActionsAsSystem([action]);
  return true;
}
public async removeUnusedAttachments(expiredOnly: boolean, options?: UpdateUsageOptions) {
  const hadChanges = await this.updateUsedAttachmentsIfNeeded();
  if (hadChanges) { await this._updateAttachmentsSize(options); }
  const rowIds = await this.docStorage.getSoftDeletedAttachmentIds(expiredOnly);
  if (rowIds.length) {
    const action: BulkRemoveRecord = ["BulkRemoveRecord", "_grist_Attachments", rowIds];
    await this.applyUserActions(makeExceptionalDocSession("system"), [action]);
  }
  try { await this.docStorage.removeUnusedAttachments(); }
  catch (e) {
    if (!String(e).match(/no such table: _gristsys_Files/)) { throw e; }  // tolerate pre-schema files
  }
}
```

**Flow:** `scanAttachmentsForUsageChanges` (SQL-side `json_each` reverse-reference sweep over attachment columns) reports rows whose used-state changed → soft-delete updates `timeDeleted` to `now` for newly-unused and `null` for newly-used (undo can resurrect) → size accounting refreshed → `getSoftDeletedAttachmentIds(expiredOnly)` selects rows soft-deleted long enough ago → those are hard-removed via a system user action (so it goes through the normal action pipeline and is undoable) → storage-level blob GC (`removeUnusedAttachments`) purges the actual files, tolerating the pre-`_gristsys_Files` schema. Runs on an hourly interval and again at shutdown so even briefly-open docs get cleaned.
**Invariant:** (1) Soft-delete is a reversible metadata flip (`timeDeleted` null = used), so undo of a removal can restore a "deleted" attachment. (2) The usage scan is run BEFORE hard-delete so a row that became used again is never purged. (3) The soft-delete update deliberately bypasses `applyUserActions` (which could block in delete-only mode) via `_applyUserActionsAsSystem`; the hard-delete uses the normal action path so it participates in history. (4) `removeUnusedAttachments` at shutdown guarantees periodic cleanup even for short-lived docs.
**Probe:** direct tests `test/server/lib/ActiveDoc.ts` attachments suite (:1225): "can enforce internal attachments limit" (:1278), "can pack attachments into an archive" (:1331), "can import missing attachments from an archive" (:1374), "updates the document's attachment usage on .tar upload" (:1386); storage-level reverse-reference scan is pinned by the `attachment-reverse-reference-scan` capsule's tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "updateUsedAttachmentsIfNeeded removeUnusedAttachments scanAttachmentsForUsageChanges", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase reversible GC: reverse-reference scan → soft-delete timestamp flip (undoable) → expired-only hard delete through the normal action pipeline → blob purge with schema-tolerance. Adapt the "expired" window and where the scan runs (interval vs shutdown). Omit Grist's `_grist_Attachments`/`_gristsys_Files` naming unless porting the schema. The `_applyUserActionsAsSystem`-vs-`applyUserActions` split (soft bypasses the gate, hard participates in history) is the subtle invariant to preserve.
