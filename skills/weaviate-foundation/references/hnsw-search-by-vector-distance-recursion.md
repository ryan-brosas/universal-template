<!-- capsule-v2 -->
# SearchByVectorDistance geometric-threshold recursion — growing-window rescan with offset arithmetic

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does Weaviate return ALL vectors within a target distance (movingAvg/"nearVector maxDistance") instead of a fixed top-k?

## Generic recursive window growth
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:1347-1487` (`searchByDistParams`, `searchByVectorDistance[T dto.Embedding]`).
**Signature:** `searchByVectorDistance[T dto.Embedding](ctx, vector T, targetDistance float32, maxLimit int64, allowList, searchByVector func(ctx, T, int, AllowList) ([]uint64, []float32, error), logger)` — generic over single/multi-vector.
**Data Shape:** params: `offset=0, limit=100 (DefaultSearchByDistInitialLimit), totalLimit=offset+limit`; multiplier 10 per iteration; `maxLimit < 0` ⇒ unlimited.

### Decisive source
```go
recursiveSearch := func() (bool, error) {
    ids, dist, err := searchByVector(ctx, vector, searchParams.totalLimit, allowList)
    ...
    ids, dist = ids[offsetCap:totalLimitCap], dist[offsetCap:totalLimitCap]  // skip already-seen prefix
    if len(ids) == 0 { return false, nil }
    lastFound := dist[len(dist)-1]
    shouldContinue = lastFound <= targetDistance        // results still inside threshold ⇒ maybe more exist
    for i := range ids {
        if aboveThresh := dist[i] <= targetDistance; aboveThresh ||
            floatcomp.InDelta(float64(dist[i]), float64(targetDistance), 1e-6) {
            resultIDs = append(resultIDs, ids[i]); resultDist = append(resultDist, dist[i])
        } else {
            break                                        // sorted ⇒ first below threshold ends scan
        }
    }
    return shouldContinue, nil
}
// loop: iterate() {offset=totalLimit; limit*=10; totalLimit=offset+limit}; stop at maxLimitReached
```

**Flow:** ask for 100 → keep those ≤ targetDistance (with 1e-6 delta tolerance for float equality at the boundary) → if the LAST returned distance was still within threshold, grow the window ×10 (offset slides past everything already consumed) and repeat → stop when a window's tail exceeds the threshold or maxLimit is hit (warn log). Results come back ascending-distance because the underlying KNN queue pops in reverse.
**Invariant:** The offset/limit bookkeeping assumes each call returns EXACTLY totalLimit ordered items until exhausted; slicing with `offsetCap/totalLimitCap` guards short tails. A porter who restarts the window at 0 re-scans duplicates; one who forgets the InDelta tolerance drops boundary elements. maxLimit=-1 means unbounded (aggregation use case) — treating it as 0 returns nothing.
**Probe:** `grep -n 'DefaultSearchByDistInitialLimit = 100\|DefaultSearchByDistLimitMultiplier = 10' adapters/repos/db/vector/hnsw/search.go` → both constants at :1364/:1370.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "searchByVectorDistance recursive limit multiplier targetDistance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the window-growth state machine verbatim including delta tolerance. Adapt the initial limit/multiplier constants as tunables. Omit the logger plumbing.
