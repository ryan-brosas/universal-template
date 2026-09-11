<!-- capsule-v2 -->
# Upload action matrix & donePaths loop guard — which of create/update/conflict fires, and how does the loop prove termination?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does the UPLOAD step decide an item's fate, and how does it distinguish "user typed during sync" from a genuinely broken target?

## UPLOAD step of Synchronizer.start
**Path/Symbol:** `packages/lib/Synchronizer.ts` :616-881 (loop), :649-660 (`donePaths` guard), :674-724 (action decision).
**Signature:** `while(true){ itemsThatNeedSync → per-item stat/get → action } ` until `result.hasMore === false`.
**Data Shape:** local rows via `BaseItem.itemsThatNeedSync(syncTargetId)`; remote truth = FULL content fetch (`apiCall('get', path)` then unserialize) because driver file mtimes are unreliable — content's own `updated_time` is the only trusted clock.

### Decisive source
```ts
if (!remote) {
    if (!local.sync_time) action = SyncAction.CreateRemote;        // never synced
    else action = getConflictType(local);                          // remote deleted, local changed
} else if (remoteContent.updated_time > local.sync_time) {
    action = getConflictType(local);                               // both changed since last sync
} else {
    action = SyncAction.UpdateRemote;                              // local has changes
}
// donePaths repeat ⇒ classify WHY before failing:
if (local.updated_time > time.unixMs() + Day) throw new Error('Remote item %s has an updated_time in the future');
else if (local.updated_time > time.unixMs()) throw new JoplinError('...updated_time in the future', 'processingPathTwice');
else if (syncItem.force_sync) throw new JoplinError('...force_sync', 'processingPathTwice');
else throw new JoplinError('...', 'changedDuringSync');            // ← user typing during sync
```

**Flow:** pre-upload batch (see ItemUploader capsule) → per item: stat (skipped for never-synced ids) → decide action → resource blob upload skipped unless `syncItem.sync_time < blob_updated_time || force_sync` (metadata-only edits don't re-push blobs; ≥10MB logs warning) → serializeAndUploadItem → on success `saveSyncTime(syncTargetId, local, local.updated_time)` (+ note base-content snapshot) → conflict actions delegated → `completeItemProcessing(path)`; loop re-runs while hasMore.
**Invariants:** (1) sync_time := updated_time AFTER successful upload — the ms-resolution race (edit in the same millisecond as upload) is documented and accepted, etag noted as the future fix (:827-839); (2) repeated-path errors are 4-way CLASSIFIED — `'changedDuringSync'` clears `hasCaughtError` (:1236-1239) so the tail re-sync trigger re-fires instead of surfacing an error; `'processingPathTwice'` is terminal info-grade; future-dated remote items (> now+1day) are a hard Error telling the user to fix the target manually; (3) master keys are never uploaded anymore (`action = null`) though kept in DB; (4) read-only target items degrade to conflicts with `itemIsReadOnly = true`, not failures.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "updated_time > time.unixMs() + Day" packages/lib/Synchronizer.ts && grep -cF "error.code === '"'"'changedDuringSync'"'"'" packages/lib/Synchronizer.ts && grep -cF "syncItem.sync_time < resource.blob_updated_time || syncItem.force_sync" packages/lib/Synchronizer.ts && grep -cF "saveSyncTime(syncTargetId, local, local.updated_time)" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 1 / 1 / 1 / 1). Direct tests: `Synchronizer.basics.test.ts` 'should skip items that cannot be synced' (:313), 'should handle items that are read-only on the sync target' (:339).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "itemsThatNeedSync donePaths processingPathTwice changedDuringSync UpdateRemote CreateRemote", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: content-clock-over-mtime rule, four-way repeat classification with non-terminal user-edit class, post-upload sync_time stamping, blob-vs-metadata split. Adapt: action enum to your engine. Omit: testingHooks branches.
