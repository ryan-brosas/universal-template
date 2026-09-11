<!-- capsule-v2 -->
# Delta step: context pagination, download queue & mid-sync target validation — how do you page remote changes without losing or double-applying any?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does the DELTA loop combine driver cursors, prefetching, and cancellation so a resumed sync is always correct?

## DELTA step of Synchronizer.start
**Path/Symbol:** `packages/lib/Synchronizer.ts` :890-1209 (loop), :901-935 (context + validation), :951-986 (download queue), :1154-1177 (context persistence rule).
**Signature:** `apiCall('delta', '', { context, allItemIdsHandler, allItemMetadataHandler, wipeOutFailSafe, logger }) → PaginatedList { hasMore, context, items }`.
**Data Shape:** `RemoteItem { path, jop_updated_time?, jopItem?, isDeleted?, updated_time }`; `supportsDeltaWithItems = items carry jopItem !== undefined`; TaskQueue `syncDownload` for parallel gets.

### Decisive source
```ts
if (lastContext.delta) context = lastContext.delta;      // resume from saved cursor
...
await checkSyncTargetIsValid(this.api());                // info.json still present after EACH page
...
const loadContent = async () => {
    if (supportsDeltaWithItems) return remote.jopItem;   // payload already in the delta response
    const task = await this.downloadQueue_.waitForResult(path);
    ...
};
...
// If user has cancelled, don't record the new context (2) so that synchronisation
// can start again from the previous context (1) next time.
if (!hasCancelled) { ... if (!listResult.hasMore) { newDeltaContext = listResult.context; break; } }
```

**Flow:** per page — call driver delta with accumulated context; re-verify target validity (failsafe against OneDrive directory swaps #11489); map paths→ids, batch-load locals; skip downloads when `supportsAccurateTimestamp && local.updated_time === remote.jop_updated_time` or when items embed payloads; else push `get` tasks into the queue and await results per item. Per remote item decide CreateLocal / UpdateLocal / DeleteLocal (see conflict capsule); folders are DEFERRED into `localFoldersToDelete` and processed after the whole loop.
**Invariants:** (1) cancel ⇒ keep OLD cursor: pages applied under cursor N+1 are idempotent updates on replay ("the update will simply be skipped" when contents equal); (2) before persisting the final context strip bulky rebuildable keys (`delete deltaToSave.statsCache; delete deltaToSave.statIdsCache`) — they're cache, not truth; (3) `deletedItemsProcessed` must be cleared when a delta completes so deletions re-scan next sync (file-api.ts :656-662); (4) content null between delta listing and get ⇒ warn + skip, resolved next sync (:1056-1058); (5) master keys downloaded are added to the store ONLY if absent from info.json (info.json is the authority); (6) resources create/update reset fetch_status IDLE first (blob fetched separately).
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "delete deltaToSave.statsCache;" packages/lib/Synchronizer.ts && grep -cF "await checkSyncTargetIsValid(this.api());" packages/lib/Synchronizer.ts && grep -cF "supportsDeltaWithItems) return remote.jopItem;" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 1 / 1 / 1). Direct test: `Synchronizer.basics.test.ts` 'should not sync deletions that came via sync even when there is a conflict' (:511).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "downloadQueue supportsDeltaWithItems newDeltaContext saveContextHandler checkSyncTargetIsValid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: old-cursor-on-cancel rule, cache-strip-before-persist, post-page target-liveness check, embedded-payload fast path, deferred folder deletion set. Adapt: queue concurrency to your platform. Omit: driver-specific delta impls (separate seam).
