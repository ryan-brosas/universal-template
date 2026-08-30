<!-- capsule-v2 -->
# L0 trigger activity cache — how do you prioritize recently-written collections without starving the idle ones?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does the trigger split collections into "active" (just received L0 writes) vs "idle" buckets, and what demotes an active collection back to idle?

## Read-count + refresh-window demotion
**Path/Symbol:** `internal/datacoord/compaction_policy_l0.go:activeCollections` (lines 177–225) and `Trigger` (51–102).
**Signature:** `func (ac *activeCollections) Record(collectionID int64)`; `func (ac *activeCollections) Read(collectionID int64)`; `func (ac *activeCollections) ClearMissCached(collectionIDs ...int64)`.
**Data Shape:** `collections map[int64]*activeCollection` under `collGuard sync.RWMutex`; each entry: `{ID int64; lastRefresh time.Time; readCount *atomic.Int64}`.

### Decisive source
```go
func (ac *activeCollections) Record(collectionID int64) {
	...
	if _, ok := ac.collections[collectionID]; !ok {
		ac.collections[collectionID] = newActiveCollection(collectionID)
	} else {
		ac.collections[collectionID].lastRefresh = time.Now()
		ac.collections[collectionID].readCount.Store(0)   // fresh write resets demotion counter
	}
}

func (ac *activeCollections) Read(collectionID int64) {
	...
	if _, ok := ac.collections[collectionID]; ok {
		ac.collections[collectionID].readCount.Inc()
		if ac.collections[collectionID].readCount.Load() >= 3 &&
			time.Since(ac.collections[collectionID].lastRefresh) > 3*paramtable.Get().DataCoordCfg.L0CompactionTriggerInterval.GetAsDuration(time.Second) {
			mlog.Info(context.TODO(), "Active(of deletions) collections become idle", ...)
			delete(ac.collections, collectionID)
		}
	}
}
```

**Flow:** Every new-L0-segment notification calls `OnCollectionUpdate` → `Record` (insert or refresh window + reset counter). Each policy `Trigger`: active set = map keys; `lo.Difference(activeColls, keys(latestCollSegs))` yields `missCached` (recorded but no longer exist) → `ClearMissCached`. Iterating all compactable collections calls `Read(collID)` per collection WITH L0 segments — third read past a full 3×trigger-interval quiet window deletes the entry (demote to idle). Views from still-active collections emit under `TriggerTypeLevelZeroViewChange`; idle ones under `TriggerTypeLevelZeroViewIDLE`, which the manager handles with `ForceTrigger` (compaction_trigger_v2.go :401–403).
**Invariant:** Active status can only delay (not cancel) compaction — idle views force-trigger regardless of minimum delta thresholds. Demotion requires BOTH three quiet reads AND 3× interval since lastRefresh; a single new write resets the whole ladder. Collections dropped from meta are garbage-collected via miss-cache diffing, never leak.
**Probe:** `internal/datacoord/compaction_policy_l0_test.go:36 TestL0CompactionPolicySuite` (suite exercises Trigger's active/idle emission); direct-source pin: demotion condition lines 212–216, reset-on-record lines 201–204.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "activeCollections l0CompactionPolicy OnCollectionUpdate", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI form: `search_graph '{"project":"ext-milvus","query":"activeCollections","limit":5,"detail":"ids"}'` → rank-1 hit `internal.datacoord.activeCollections Struct internal/datacoord/compaction_policy_l0.go 177-180`.)

## Verdict
Adopt write-refresh + quiet-window demotion for any write-biased work-prioritization cache. Adapt thresholds (3 reads / 3 intervals) to your tick cadence. Omit milvus trigger-type mapping. Caveat: cgo-blocked runner; direct source + upstream suite read at pin.
