<!-- capsule-v2 -->
# Flat-search cutoff — tiny allow-lists bypass the graph entirely

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** When should a filtered search scan linearly instead of walking HNSW?

## Cutoff ladder in SearchByVector
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:80-94` (`SearchByVector`), `flat_search.go:28-142` (`flatSearch`).
**Signature:** `SearchByVector(ctx, vector []float32, k int, allowList helpers.AllowList)`; `flatSearchConcurrency` from config (min 1).
**Data Shape:** `h.flatSearchCutoff int64` (atomic-loaded user config); workers stride `idPos := workerID; idPos += h.flatSearchConcurrency` over the materialized candidate slice.

### Decisive source
```go
vector = h.normalizeVec(vector)
flatSearchCutoff := int(atomic.LoadInt64(&h.flatSearchCutoff))
if allowList != nil && !h.forbidFlat && allowList.Len() < flatSearchCutoff {
    helpers.AnnotateSlowQueryLog(ctx, "hnsw_flat_search", true)
    return h.flatSearch(ctx, vector, k, h.searchTimeEF(k), allowList)
}
return h.knnSearchByVector(ctx, vector, k, h.searchTimeEF(k), allowList)
```
flatSearch internals: `if !h.shouldRescore() || h.muvera.Load() { limit = k }` — over-fetch to ef ONLY when rescoring will follow; per-worker local max-queues merged under one mutex; `addResult` replaces the top when full.

**Flow:** allow-list smaller than cutoff ⇒ brute-force exactly those ids (nil allow-list or `forbidFlat` test flag ⇒ always graph). Each worker skips ids ≥ nodes-length (issue #1937 hot-fix), nil vertices, and tombstones; distance errors of type `storobj.ErrNotFound` self-heal via `handleDeletedNode`. Rescoring (compressed indexes) then runs on the flat result queue identically to the graph path.
**Invariant:** The cutoff comparison is `<` against `allowList.Len()` — an equal-size list goes through the graph. Forgetting `shouldRescore()`'s limit clamp makes flat search return ef results that later get cut to k, wasting rescore work; forgetting it in the muvera branch crashes downstream scoring.
**Probe:** `grep -n 'func (h \*hnsw) flatSearch' adapters/repos/db/vector/hnsw/flat_search.go` → line 28 (single definition; `hfresh.flatSearch` lives in another package).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "flatSearch", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the cutoff ladder + worker-stride merge pattern. Adapt `addResult`'s bounded max-heap to your priority queue. Omit slow-query annotation.
