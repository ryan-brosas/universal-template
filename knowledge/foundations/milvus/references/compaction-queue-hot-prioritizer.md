<!-- capsule-v2 -->
# Hot-swappable queue prioritizer — how do you change a live priority function without dropping queued items or re-prioritizing on every tick?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does a scheduler swap its ordering policy at runtime from config, cheaply on every scheduling tick, while keeping every queued task?

## Name-keyed prioritizer sync + heap re-init
**Path/Symbol:** `internal/datacoord/compaction_queue.go:CompactionQueue` (lines 87–166) and `internal/datacoord/compaction_queue.go:LevelPrioritizer/MixFirstPrioritizer/DefaultPrioritizer` (lines 193–227).
**Signature:** `func (q *CompactionQueue) SyncPrioritizer(name string)`; `type Prioritizer func(t CompactionTask) int`; `func getPrioritizerByName(name string) Prioritizer`.
**Data Shape:** `pq PriorityQueue[CompactionTask]` (generic `container/heap`), `prioritizer Prioritizer`, `prioritizerName *string` (pointer because `""` is a settable config value under RESTful alterConfig — only null resets, so string zero-value cannot mean "unset", comment lines 90–100), `capacity int`.

### Decisive source
```go
func (q *CompactionQueue) SyncPrioritizer(name string) {
	q.lock.Lock()
	defer q.lock.Unlock()
	if q.prioritizerName != nil && *q.prioritizerName == name {
		return // unchanged config => no-op, safe every tick
	}
	q.prioritizerName = &name
	q.updatePrioritizerLocked(getPrioritizerByName(name))
}

func (q *CompactionQueue) updatePrioritizerLocked(prioritizer Prioritizer) {
	q.prioritizer = prioritizer
	for i := range q.pq {
		q.pq[i].priority = q.prioritizer(q.pq[i].value)
	}
	heap.Init(&q.pq)
}
```

**Flow:** Every schedule tick calls `SyncPrioritizer(getPrioritizerName())`. Same-name sync is one lock + one string compare (re-prioritize loop iterates zero times). A changed name resolves the new func (`"level"` → L0=1/mix=10/clustering=100; `"mix"` → mix=1/L0=10; default → int(PlanID)), recomputes EVERY stored priority with the new func, then `heap.Init` rebuilds the heap in O(n). `UpdatePrioritizer` (out-of-band injection) nils the name so the next sync re-adopts config. `Enqueue` computes priority at insert time; capacity>0 returns internal sentinel `errFull`.
**Invariant:** No item is ever dropped or reordered across the swap except through the new priority function; priorities are always consistent with exactly one prioritizer version. The name pointer must distinguish "never synced" (nil) from "synced to empty-string". Internal sentinels `errFull`/`errNoSuchElement` are caught by `errors.Is` and never serialized across gRPC (comment lines 77–83).
**Probe:** `internal/datacoord/compaction_queue_test.go:186 TestCompactionQueue_SyncPrioritizer` — observes recompute by priming with DefaultPrioritizer (priority=int(PlanID)), mutating PlanID after enqueue, asserting 100 same-name syncs leave the stale priority untouched, then switching to "level" and asserting the value recomputes. Sub-test comments explain why "mix" would be a vacuous assertion (MixFirstPrioritizer also yields 1 for MixCompaction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "CompactionQueue SyncPrioritizer UpdatePrioritizer LevelPrioritizer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the name-keyed no-op sync + full-recompute-on-change design for any hot-configurable scheduler. Adapt priority domains to your task types. Omit milvus's specific numeric tiers unless porting compaction semantics wholesale. Caveat: runner needs cgo; evidence is direct source plus upstream unit tests read at pin.
