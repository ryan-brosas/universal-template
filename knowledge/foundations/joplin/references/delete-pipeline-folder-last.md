<!-- capsule-v2 -->
# Delete pipeline & folder-last rule — how do deletions propagate in both directions without cascades or loops?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does DELETE_REMOTE work, and how are remote-deleted folders handled so children never vanish wrongly?

## syncDeleteStep + deferred local folder deletion
**Path/Symbol:** `packages/lib/services/synchronizer/utils/syncDeleteStep.ts` :14-183; consumer `packages/lib/Synchronizer.ts` :592-607 (DELETE_REMOTE), :1136-1140 + :1179-1204 (deferred folders).
**Signature:** `syncDeleteStep(syncTargetId, cancelling, logSyncOperation, apiCall, api, dispatch)`.
**Data Shape:** `deleted_items` table rows `{ item_type, item_id, deleted_time }` per sync target.

### Decisive source
```ts
// syncDeleteStep: batch first (20/batch), then individual; resources delete blob too
const supportsBatchDelete = api.supportsMultiDelete;
...
await apiCall('delete', path);
if (isResource) await apiCall('delete', resourceRemotePath(item.item_id));
...
if (error.code === 'isReadOnly') {
    // target refuses deletion ⇒ RE-DOWNLOAD the item locally (undelete)
    let remoteContent = await apiCall('get', path);
    ...
    await ItemClass.save(remoteContent, { isNew: true, autoTimestamp: false, changeSource: ItemChange.SOURCE_SYNC, nextQueries });
}

// Synchronizer delta loop: folders are collected, not deleted inline
if (action === SyncAction.DeleteLocal && local.type_ === BaseModel.TYPE_FOLDER) {
    localFoldersToDelete.add(local.id);
    continue;
}
// ...after the whole loop:
for (const folderId of localFoldersToDelete) {
    const noteIds = await Folder.noteIds(folderId);
    if (noteIds.length) { logger.warn('Conflict: Folder to be deleted', folderId, 'still contains notes', noteIds);
        await Folder.markNotesAsConflict(folderId); }        // non-empty deletion = conflict
    await Folder.delete(folderId, { deleteChildren: false, trackDeleted: false, changeSource: ItemChange.SOURCE_SYNC, sourceDescription: 'Sync' });
}
```

**Flow:** DELETE_REMOTE runs BEFORE upload: batched 20-at-a-time when the driver supports multi-delete (`methodNotSupported` flips to individual mode permanently for this run); read-only refusal re-saves the still-existing remote item locally with fresh sync times (the deletion is reverted rather than retried forever); malformed remote payloads during undelete are skipped via remoteDeletedItems bookkeeping. On the incoming side, a recreated folder cancels its pending deletion (`localFoldersToDelete.delete(remoteId)` :1013-1016).
**Invariants:** (1) folders ALWAYS die last and only if empty — surviving notes are marked conflict instead of being destroyed ("whatever deleted them should have deleted their content too"); (2) `trackDeleted: false` on all sync-driven deletes prevents echo entries that would re-delete remotely (test 'should not created deleted_items entries for items deleted via sync' basics:185); (3) every successful remote delete immediately removes the deleted_items row (`remoteDeletedItems`) — crash-safe idempotence; (4) batch errors fall back per-item, never abort the step.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "await Folder.markNotesAsConflict(folderId);" packages/lib/Synchronizer.ts && grep -cF "deleteChildren: false," packages/lib/Synchronizer.ts && grep -cF "error.code === '"'"'isReadOnly'"'"'" packages/lib/services/synchronizer/utils/syncDeleteStep.ts'` (anchored at repo root; expects 1 / ≥1 / 1). Direct tests: `Synchronizer.basics.test.ts` delete family (:108-262 incl. cross-delete-all-folders).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "syncDeleteStep batchDeleteStep deleted_items markNotesAsConflict localFoldersToDelete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: tombstone-table delete ledger with immediate row removal, batch-with-fallback, readonly-refusal-as-undelete, folders-last-empty-check rule. Adapt: batching size/mechanics. Omit: resource blob paths.
