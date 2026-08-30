<!-- capsule-v2 -->
# basicDelta for dumb targets — how do you detect remote changes (and deletions!) with only a directory listing?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** What is the fallback delta algorithm when the target has no cursor API, and how does it avoid wiping user data on an empty-looking directory?

## basicDelta
**Path/Symbol:** `packages/lib/file-api.ts` :496-669 (`basicDelta`), :463-491 (`BasicDeltaContext` + builder); enhancement gate :69-77 (`enableEnhancedBasicDeltaAlgorithm`).
**Signature:** `basicDelta(path, getDirStatFn, options): Promise<{ hasMore, context, items }>`; page size `outputLimit = 50`.
**Data Shape:** context `{ timestamp, filesAtTimestamp, statsCache, statIdsCache, deletedItemsProcessed }`; items = ItemStat[] or `{ path, isDeleted: true }` markers.

### Decisive source
```ts
if (stat.updated_time < context.timestamp) continue;              // older than cursor: skip
if (stat.updated_time === context.timestamp) {                    // same-ms tie:
    if (context.filesAtTimestamp.indexOf(stat.path) >= 0) continue; // already seen → skip
}
if (stat.updated_time > newContext.timestamp) {
    newContext.timestamp = stat.updated_time;
    newContext.filesAtTimestamp = [];                             // new max: reset tie set
}
newContext.filesAtTimestamp.push(stat.path);
...
const percentDeleted = itemIds.length ? deletedItems.length / itemIds.length : 0;
// If more than 90% of the notes are going to be deleted, it's most likely a
// configuration error or bug... we don't wipe out the user data
if (options.wipeOutFailSafe && percentDeleted >= 0.90)
    throw new JoplinError('...Fail-safe...', 'failSafe');
output = output.concat(deletedItems);
```

**Flow:** one dir listing cached in context until pagination completes (`statsCache`) → per file: classic mode advances `timestamp` high-water and tracks the exact-timestamp tie set (an item modified during the delta run at the SAME ms is still caught next pass via filesAtTimestamp); enhanced mode instead compares each stat against locally persisted metadata (`allItemMetadataHandler`), catching timestamp DECREASES caused by external sync services (filesystem targets always; WebDAV only for localhost/127.x/[::1] — regex-gated). Deletion detection = binary-search of local synced ids against listed ids, computed once per sync (`deletedItemsProcessed` latch cleared on final page).
**Invariants:** (1) deletions ride OUTSIDE outputLimit ("delete operations are cheap") but only on the first pass of a sync; (2) the ≥90%-deleted failsafe is the data-loss firewall for moved dirs / disconnected network drives returning empty listings — direct test 'should not wipe out user data when syncing with an empty target' (`Synchronizer.basics.test.ts`:484) proves notes survive AND that disabling the flag really deletes; (3) statsCache/statIdsCache are stripped from any SAVED context (Synchronizer strips them too) — rebuildable cache never becomes truth; (4) non-system paths and directories are skipped before comparison.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "percentDeleted >= 0.90" packages/lib/file-api.ts && grep -cF "const outputLimit = 50;" packages/lib/file-api.ts && grep -cF "delete newContext.deletedItemsProcessed" packages/lib/file-api.ts'` (anchored at repo root; expects 1 / 1 / 1). Direct tests: `packages/lib/file-api.test.ts` parametrized basicDelta suite (:243-313, both algorithm modes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "basicDelta wipeOutFailSafe filesAtTimestamp statIdsCache deletedItemsProcessed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: high-water+tie-set listing diff, binary-search deletion detection with %-deleted failsafe, cache-until-paginated pattern. Adapt: page size, metadata handler shape. Omit: driver stat implementations.
