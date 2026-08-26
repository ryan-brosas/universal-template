<!-- capsule-v2 -->
# Sync lifecycle orchestration — what must run before, between, and after the three sync steps?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** What is the exact pre-sync preparation and post-sync maintenance choreography around upload/delete_remote/delta?

## Synchronizer.start skeleton
**Path/Symbol:** `packages/lib/Synchronizer.ts` :404-596 (prelude), :592-607 vs :616-881 (step ORDER: delete_remote BEFORE update_remote despite comment numbering), :890-1209 (delta), :1257-1322 (epilogue).
**Signature:** `start(options: SyncStartOptions): Promise<outputContext>`; `syncSteps` default `['update_remote','delete_remote','delta']`.
**Data Shape:** `outputContext = { ...lastContext }`; only `.delta` is ever written back.

### Decisive source
```ts
if (this.state() !== 'idle') { error.code = 'alreadyStarted'; throw error; }
this.state_ = 'in_progress';
...
await this.resourceService().indexNoteResources();     // flag orphans pre-sync (best-effort try/catch)
await this.shareService_.maintenance();                 // fetch invitations, clear stale share_ids
await Folder.updateAllShareIds(...);                    // IsReadOnly errors swallowed by design
...
const itemUploader = new ItemUploader(this.api(), this.apiCall);
await this.api().initialize();
this.api().setTempDirName(Dirnames.Temp);
... // info.json version gate + LWW merge (own capsules)
syncLock = await this.lockHandler().acquireLock(LockType.Sync, ...);
this.lockHandler().startAutoLockRefresh(syncLock, ...);
// steps: delete_remote → update_remote → delta (comments numbered 2/1/3 — execution order wins)
```

**Flow:** single-flight guard (`alreadyStarted`) → resource indexing + share maintenance (each individually best-effort: log-and-continue so a broken indexer never blocks sync) → share_id normalization with read-only tolerance → api init + temp dir → remote info gate/merge → sync-lock + auto-refresh → delete_remote → update_remote (with pre-upload batching) → delta (+ folder-last deletion + deleteOrphanSyncItems) → epilogue.
**Invariants:** (1) DELETE_REMOTE precedes UPLOAD so tombstones clear the way and uploads can't resurrect deleted paths; (2) every pre-service is failure-isolated EXCEPT the info.json plane which aborts; (3) outputContext carries ONLY the delta cursor — callers persist one resume key regardless of how many pages ran; (4) `isFullSync` = all three step names present in this run's syncSteps (partial runs report partial); (5) cancellation is cooperative — checked between items, between pages, inside loops via `this.cancelling()`; download queue stopped but NOT nulled on cancel so trailing results remain readable (:304-322).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "error.code = '"'"'alreadyStarted'"'"';" packages/lib/Synchronizer.ts && grep -n "indexOf('"'"'delete_remote'"'"')" packages/lib/Synchronizer.ts | head -1 && grep -cF "await BaseItem.deleteOrphanSyncItems();" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 1 / line 592 (< update_remote's 616) / 1). Direct tests: `Synchronizer.basics.test.ts` whole suite exercises ordering implicitly (delete-before-upload cases :108-262).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "Synchronizer start alreadyStarted indexNoteResources setTempDirName deleteOrphanSyncItems", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: step order (delete→upload→delta), best-effort isolation for auxiliary services vs hard-fail for info plane, single-cursor output contract, cooperative cancellation points. Adapt: services to your app domain. Omit: share/E2EE specifics (separate seams).
