<!-- capsule-v2 -->
# SWEEPING filtered layer search — filter at result-insert, never at traversal (except RRE)

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** In the default strategy, WHERE is the allow-list enforced so the graph stays connected while results stay correct?

## Result-side filtering with worst-distance early exit
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:301-557` (main loop), `:573-608` (`insertViableEntrypointsAsCandidatesAndResults`).
**Signature:** `searchLayerByVectorWithDistancerWithStrategy(ctx, queryVector, entrypoints *priorityqueue.Queue[any], ef, level int, allowList, compressorDistancer, strategy) (*Queue, error)`.
**Data Shape:** `candidates` min-queue(ef) / `results` max-queue(ef); batch distancer computes all unvisited neighbor distances in one call (`DistancesToNodes` with `floatPrefetchAhead = 4` software prefetching).

### Decisive source
```go
for candidates.Len() > 0 {
    candidate := candidates.Pop()
    if dist > worstResultDistance && results.Len() >= ef { break }   // classic HNSW stop
    ...
    for i, neighborID := range unvisited {
        distance := neighborDists[i]
        // ErrNotFound ⇒ handleDeletedNode (tombstone + skip), NOT a hard failure
        if distance < worstResultDistance || results.Len() < ef {
            candidates.Insert(neighborID, distance)                   // ALWAYS traverse
            if strategy == SWEEPING && level == 0 && allowList != nil {
                if !allowList.Contains(neighborID) { continue }       // but only insert allowed
            }
            if h.hasTombstone(neighborID) { continue }
            results.Insert(neighborID, distance)
            if results.Len() > ef { results.Pop() }
            if results.Len() > 0 { worstResultDistance = results.Top().Dist }
        }
    }
}
```

**Flow:** every unvisited neighbor within the current worst-result bound enters `candidates` — filtering NEVER blocks traversal in SWEEPING. The allow-list gates only what lands in `results`, and only at level 0. Entrypoint seeding applies the same gate (`insertViableEntrypointsAsCandidatesAndResults`: allowed-only into results, everything still visited). If the entrypoint itself is filtered out, `currentWorstResultDistance*` returns `math.MaxFloat32` so any allowed candidate compares favorably (:627-633 comment).
**Invariant:** Filtering candidates instead of results breaks recall catastrophically (the walk dies at the first filtered node). The tombstone check happens AFTER the allow-list check and only on insertion; deleted-in-store vectors surface as typed `storobj.ErrNotFound` per-neighbor errors which self-heal via `handleDeletedNode` (adds tombstone, skips) — turning that into a returned error aborts searches under concurrent deletes.
**Probe:** `grep -c 'insertViableEntrypointsAsCandidatesAndResults' adapters/repos/db/vector/hnsw/search.go` → 2; direct test `adapters/repos/db/vector/hnsw/search_test.go::TestRescore` (:245) exercises the shared result queue; `TestAcornPercentage` (:191) pins the sibling path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "SWEEPING strategy allow list level 0 results insert worstResultDistance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt traverse-everything/filter-results with the MaxFloat32 empty-results fallback. Adapt the batch distancer (prefetch depth 4) to your cache; omit Prometheus annotations.
