<!-- capsule-v2 -->
# ACORN two-hop neighbor expansion — how a filtered graph walk escapes filtered-out dead zones

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does ACORN build its candidate neighbor set so a filter that removes most nodes doesn't strand the walk?

## ε-neighborhood expansion inside the candidate loop
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:365-466` (ACORN branch inside `searchLayerByVectorWithDistancerWithStrategy`).
**Signature:** inline block building `connectionsReusable[:realLen]` per candidate.
**Data Shape:** three pooled uint64 slices (`sliceConnectionsReusable` cap 8×M0, `slicePendingNextRound`, `slicePendingThisRound` cap M0 where M0 = `maximumConnectionsLayerZero`); TWO visited lists: `visited` (final expansion set) and `visitedExp` (BFS frontier dedupe).

### Decisive source
```go
hop := 1
maxHops := 2
for hop <= maxHops && realLen < 8*h.maximumConnectionsLayerZero && len(pendingNextRound) > 0 {
    // copy pendingNextRound→pendingThisRound; reset pendingNextRound
    for index < len(pendingThisRound) && realLen < 8*h.maximumConnectionsLayerZero {
        nodeId := pendingThisRound[index]; index++
        if ok := visited.Visited(nodeId); ok { continue }        // already in expansion
        if !visitedExp.CheckAndVisit(nodeId) {
            if allowList.Contains(nodeId) {                       // hop-1: direct neighbors
                connectionsReusable[realLen] = nodeId; realLen++; continue
            }
        } else {
            continue                                              // hop-2 member already handled
        }
        // not allowed ⇒ expand ITS neighbors (hop 2)
        iterator := node.connections.ElementIterator(uint8(level))
        for iterator.Next() {
            _, expId := iterator.Current()
            ...
            if allowList.Contains(expId) { connectionsReusable[realLen] = expId; realLen++ }
            else if hop < maxHops { pendingNextRound = append(pendingNextRound, expId) }
        }
    }
    hop++
}
```

**Flow:** start from the candidate's direct connections (hop 1). Allowed neighbors go straight into `connectionsReusable` (cap 8×M0 ≈ 8×maxConnectionsLayerZero, i.e. 16×M for default M=32... concretely 8×M0 with M0=2M). Filtered-out neighbors are not discarded — their ids are queued in `pendingNextRound`, and one more BFS ring (hop ≤ 2) collects THEIR allowed neighbors. Both visited lists bound the traversal; the whole thing stays inside the candidate's node lock.
**Invariant:** The cap `8*maximumConnectionsLayerZero` on `realLen` is load-bearing: exceeding it would overflow the pooled slice (the SWEEPING branch has a legacy-bug fallback reallocating when `connections.LenAtLayer > M0`, issue #1868/#1897 — do NOT port that branch into the ACORN path). Multivector indexes resolve node-id→doc-id via `compressor.GetKeys/cache.GetKeys` BEFORE the allow-list test — filtering on raw node ids there returns wrong results.
**Probe:** `grep -c 'visitedExp' adapters/repos/db/vector/hnsw/search.go` → 6; `grep -n 'maxHops := 2' adapters/repos/db/vector/hnsw/search.go` → line 376.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "ACORN two-hop neighbor expansion pendingNextRound visitedExp", limit: 10, fields: ["signature", "name", "file"] });
```
(If BM25 misses, the decisive method resolves rank-1 via query "searchLayerByVectorWithDistancerWithStrategy".)

## Verdict
Adopt the bounded two-hop BFS with dual visited sets and the 8×M0 cap. Adapt slice pooling to your allocator; omit the multivector doc-id remap if you have no compressed/multi-vector mode.
