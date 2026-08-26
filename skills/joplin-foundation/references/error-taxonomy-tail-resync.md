<!-- capsule-v2 -->
# Error-code taxonomy & tail re-sync — which failures end the sync, and how do late edits get a second chance?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does start() convert exceptions into UI outcomes, and what guarantees changes made mid-sync are not stranded?

## Catch ladder + completion epilogue
**Path/Symbol:** `packages/lib/Synchronizer.ts` :1210-1255 (catch), :1257-1322 (epilogue), :380-397 (`apiCall` lock re-wrap).
**Signature:** single catch over the whole three-step body; `throwOnError` option flips to rethrow for tests.
**Data Shape:** `progressReport_.errors[]` accumulates user-facing failures; string codes drive classification.

### Decisive source
```ts
} else if (error && ['cannotEncryptEncrypted', 'noActiveMasterKey', 'processingPathTwice', 'failSafe', 'lockError', 'outdatedSyncTarget'].indexOf(error.code) >= 0) {
    logger.info(error.message);                    // common/user-resolvable → info only
    if (error.code === 'failSafe' || error.code === 'lockError') { ...progressReport_.errors.push... }
} else if (error.code === 'changedDuringSync') {
    hasCaughtError = false;                        // NOT an error: user typed during sync
    logger.info(error.message);
} else {
    ... // retryable network errors kept OUT of the report (unless local WebDAV where timeout = down server)
}
...
if (syncLock) { this.lockHandler().stopAutoLockRefresh(syncLock); await this.lockHandler().releaseLock(LockType.Sync, ...); }
this.state_ = 'idle';
if (errorToThrow) throw errorToThrow;
// IMPORTANT: This must be the very last step in the sync...
if (!hasErrors && !hasCaughtError && !cancelledBeforeClearedState && !this.cancelling()) {
    const result = await BaseItem.itemsThatNeedSync(syncTargetId);
    if (result.items.length > 0) {
        logger.info('There are more outgoing changes to sync, schedule the sync again');
        void reg.scheduleSync(reg.syncAsYouTypeInterval(), { syncSteps }, true);
```

**Flow:** any apiCall failure is first re-wrapped if a lock anomaly explains it (`lockError` with original message preserved so handlers don't mis-classify as cannotSyncItem); catch ladder sorts into: info-grade user-actionable codes / non-error changedDuringSync / retryable-transport (unreported) / everything else reported; MUST_UPGRADE_APP + unknownItemType dispatch special actions. Epilogue ALWAYS: post-sync published-notes refresh (skipped on error), lock release + refresh stop, cancel-flag reset with pre-clear latch, SYNC_COMPLETED dispatch (isFullSync = all three steps ran), state idle, THEN optional throw.
**Invariants:** (1) state_ returns to idle even on error — a stuck in_progress bricks future syncs (start throws alreadyStarted); (2) the tail itemsThatNeedSync check is deliberately LAST so no window exists where completed-but-dirty misleads the user into closing the app; (3) cancelledBeforeClearedState distinguishes "cancel requested but flag not yet cleared" to suppress the immediate re-schedule; (4) fetchRequestCanBeRetried errors stay out of progressReport unless local WebDAV (where timeouts mean a dead server, not flaky network).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "'"'"'processingPathTwice'"'"'" packages/lib/Synchronizer.ts && grep -n "reg.scheduleSync(reg.syncAsYouTypeInterval(), { syncSteps }, true)" packages/lib/Synchronizer.ts | wc -l && grep -cF "this.state_ = '"'"'idle'"'"';" packages/lib/Synchronizer.ts'` (anchored at repo root; expects ≥1 / 1 / 1 — the third pattern matches ONLY the epilogue assignment :1302; the field declaration at :91 reads `private state_ = 'idle';` without the `this.` prefix and must not be counted). Direct tests: basics suite (:556 version-mismatch error path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "progressReport errors changedDuringSync scheduleSync alreadyStarted isFullSync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: code-ladder classification with explicit non-error class, always-idle epilogue ordering, tail re-sync trigger. Adapt: codes to your error type. Omit: redux dispatch specifics.
