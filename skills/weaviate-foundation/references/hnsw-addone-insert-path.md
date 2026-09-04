<!-- capsule-v2 -->
# addOne insert path — first-insert Once, maintenance flag, entrypoint promotion double-check

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** What is the exact insertion sequence for one node, and which steps race if done in the wrong order?

## AddBatch → addOne → findAndConnectNeighbors → promote
**Path/Symbol:** `adapters/repos/db/vector/hnsw/insert.go:188-271` (`AddBatch`), `:445-562` (`addOne`), `:572-611` (`insertInitialElement`, `generateLevel`).
**Signature:** `AddBatch(ctx, ids []uint64, vectors [][]float32) error`; `addOne(ctx, vector []float32, node *vertex) error`; `generateLevel() uint8 = floor(-log(max(rand,1e-19)) * levelNormalizer)` with `levelNormalizer = 1/log(MaxConnections)`.
**Data Shape:** `initialInsertOnce *sync.Once` (reset on graph reset); `deleteVsInsertLock.RLock` held per insert; `compressActionLock.RLock` guards the compressed/cache/compressor trio reads; levels drawn per element inside the batch.

### Decisive source
```go
h.initialInsertOnce.Do(func() {
    if h.isEmpty() { wasFirst = true; firstInsertError = h.insertInitialElement(node, vector) }
})
if wasFirst { return firstInsertError }        // empty-graph parallel import: exactly ONE winner
node.markAsMaintenance()                       // searches must skip me until fully linked
defer node.unmarkAsMaintenance()
// read global EP + maxLayer under RLock; commitLog.AddNode(node); nodes[id]=node under sharded lock;
// Preload into cache/compressor (single-vector only)
entryPointID, err = h.findBestEntrypointForNode(ctx, currentMaximumLayer, targetLevel, entryPointID, vector, distancer)
h.findAndConnectNeighbors(ctx, node, entryPointID, vector, distancer, targetLevel, currentMaximumLayer, helpers.NewAllowList())
node.unmarkAsMaintenance()                     // explicit clear BEFORE promotion
if targetLevel > h.currentMaximumLayer {
    h.Lock()
    if targetLevel > h.currentMaximumLayer {   // re-check: RUnlock→Lock gap
        h.commitLog.SetEntryPointWithMaxLayer(nodeId, targetLevel)
        h.entryPointID = nodeId; h.currentMaximumLayer = targetLevel
    }
    h.Unlock()
}
```

**Flow:** batch validates dims once (`trackDimensionsOnce`, PQ segment divisibility), alloc-checks memory estimate (len*4+30B/vector), grows the node slice under compress lock, then inserts serially. First node on an empty graph becomes entrypoint at layer 0 through a sync.Once so concurrent imports can't each claim it. Every subsequent insert: mark maintenance → persist node → descend layers via greedy ef=1 searches → connect neighbors at each level ≤ min(target,currentMax) → clear maintenance → promote to entrypoint iff its sampled level exceeds the current maximum (double-checked write).
**Invariant:** The maintenance flag between AddNode and unmark is what makes concurrent searches skip half-linked nodes (search checks `isUnderMaintenance()` before adopting candidates/entrypoints). Clearing it BEFORE the promotion branch matters — the comment at :537-539 says the defer alone is too late. `insertInitialElement` runs under full h.Lock and resets `initialInsertOnce` only in `resetUnlocked`.
**Probe:** direct tests `add_batch_test.go` + `TestDelete_EntrypointIssues` family; anchor `grep -c 'initialInsertOnce' adapters/repos/db/vector/hnsw/insert.go` → 1 (the Do call; the field lives in index.go).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "AddBatch insert initial element entrypoint level", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Once-guarded first insert, maintenance window, and double-checked promotion. Adapt level sampling constants (M, multiplier) as config. Omit insert metrics.
