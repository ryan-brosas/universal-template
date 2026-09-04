<!-- capsule-v2 -->
# Tombstone lifecycle — lazy delete marks, cycle-capped cleanup, memory-pressure abort

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How are deletes applied to the graph without rebuilding it, and how does cleanup avoid both starvation and OOM?

## Delete → tombstone → periodic reassign+remove
**Path/Symbol:** `adapters/repos/db/vector/hnsw/delete.go:49-108` (`Delete` lock stack), `:233-297` (`copyTombstonesToAllowList` caps), `:306-452` (`cleanUpTombstonedNodes` orchestration), `:505-517` (concurrency env).
**Signature:** `Delete(ids ...uint64) error`; `CleanUpTombstonedNodes(shouldAbort cyclemanager.ShouldAbortCallback) error`.
**Data Shape:** `tombstones map[uint64]struct{}` under `tombstoneLock`; `tombstoneCleanupMemoryNeeded = 100*1024*1024`; env knobs `TOMBSTONE_DELETION_MIN_PER_CYCLE` (default 0 = always run), `TOMBSTONE_DELETION_MAX_PER_CYCLE` (default MaxInt64), `TOMBSTONE_DELETION_CONCURRENCY` (default GOMAXPROCS/2 min 1).

### Decisive source
```go
func (h *hnsw) Delete(ids ...uint64) error {
	h.deleteVsInsertLock.Lock()      // excludes inserts entirely during deletes
	defer h.deleteVsInsertLock.Unlock()
	h.deleteLock.Lock()              // deletes are sequential among themselves
	defer h.deleteLock.Unlock()
	if err := h.addTombstone(ids...); err != nil { return err }
	for _, id := range ids {
		if h.getEntrypoint() == id { // tombstoned EP would strand future inserts edge-less
			denyList := h.tombstonesAsDenyList()
			if onlyNode, err := h.resetIfOnlyNode(node, denyList); err != nil { ... }
			else if !onlyNode { h.deleteEntrypoint(node, denyList) }
		}
	}
}
// cleanup: CAS single-flight; panic recover; copy tombstones→allowList honoring min/max caps;
// allocChecker pre-check + 500ms ticker monitor cancels memCtx mid-cycle on pressure;
// then reassignNeighborsOf (parallel workers claim ids via atomic counter, skip EP,
// markAsMaintenance + reconnectNeighboursOf only when connectionsPointTo(deleteList));
// replaceDeletedEntrypoint; removeTombstonesAndNodes; resetIfEmpty.
```

**Flow:** delete = tombstone stamp (+ commit-log record) — nothing else. If the victim IS the entrypoint: reset the whole index when it's the only live node, else elect a new global entrypoint now (so parallel imports never attach to a corpse). Cleanup runs as a registered cycle: single-flight CAS gate, min-tombstones skip (avoid locking the graph for nothing), max-cap batch (bounded cycle time), memory pre-check plus ticker abort, THEN neighbor reassignment (only nodes actually pointing at victims get rebuilt, under maintenance flag so searches skip them) and finally node/tombstone removal with cache eviction.
**Invariant:** Order matters: reassign BEFORE removing nodes (removing first strands edges forever); maintenance-flagged nodes must be skipped by searches (candidateNode nil / `isUnderMaintenance` checks in search.go :921, :610). `resetIfOnlyNode` accepts a benign TOCTOU window between check and reset (comment :185-187) — do not "fix" by holding all striped locks across the reset.
**Probe:** `grep -n 'tombstoneCleanupMemoryNeeded = ' adapters/repos/db/vector/hnsw/delete.go` → line 43 (100MB); direct tests: `TestDelete_WithCleaningUpTombstonesOnce` (:153), `TestTombstoneCleanupAbortsOnMemoryPressure_MidCleanup` (periodic_tombstone_removal_test.go :216), `TestDelete_ResetLockDoesNotLockForever` (:958).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "tombstone cleanup reassignNeighborsOf delete entrypoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full lifecycle including env knobs and memory-pressure abort. Adapt the allocChecker to your memory watchdog. Omit Sentry/panic-reporting glue.
