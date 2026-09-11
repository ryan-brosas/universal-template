<!-- capsule-v2 -->
# Multivector doc-id mapping — vec-id vs doc-id id spaces, purge-before-retry, late-interaction scoring

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does a multi-vector index map N vec-ids to one doc-id, survive partial-batch failures, and score ColBERT-style?

## AddMultiBatch mapping bookkeeping
**Path/Symbol:** `adapters/repos/db/vector/hnsw/insert.go:273-443` (`AddMultiBatch`), `search.go:1046-1152` (`knnSearchByMultiVector`, `computeLateInteraction`), `index.go:823-838` (`ContainsDoc`).
**Signature:** `AddMultiBatch(ctx, docIDs []uint64, vectors [][][]float32) error`.
**Data Shape:** `docIDVectors map[uint64][]uint64` (in-memory doc→vecIds); lsmkv bucket `<id>_mv_mappings` persists vecId→docId big-endian 8-byte keys; muvera mode instead stores `<id>_muvera_vectors` docId→fused float vector.

### Decisive source
```go
// whole-task retry support: purge state left by a previously failed attempt
var purge []uint64
for _, docID := range docIDs { if _, ok := h.docIDVectors[docID]; ok { purge = append(purge, docID) } }
if len(purge) > 0 { h.DeleteMulti(purge...) }          // delete stale vecs+mappings first
seenInBatch := make(map[uint64]struct{}, len(docIDs))
for i, docID := range docIDs {
    if _, dup := seenInBatch[docID]; dup { h.DeleteMulti(docID) }   // duplicate doc in same batch ⇒ last wins
    counter := h.vecIDcounter; h.vecIDcounter += uint64(numVectors);   // reserve contiguous vec-id block under h.Lock
    ids := counter..counter+numVectors-1
    h.cache.PreloadMulti(docID, ids, vectors[i])        // or compressor.PreloadMulti
    h.docIDVectors[docID] = append(h.docIDVectors[docIDs[i]], nodeId)
    store.Bucket(id+"_mv_mappings").Put(nodeIDBytes, docIDBytes)
    ... addOne per vec ...
}
// search: kPrime := k per query-vector KNN union → candidate doc set → computeLateInteraction:
similarity += maxSim over docVecs for EACH queryVec (sum of per-query minimum distances), workers stride ids,
budget-aware: workers = max(1, min(BudgetFromCtx(ctx, rescoreConcurrency), rescoreConcurrency, len(ids)))
```

**Flow:** each doc reserves a contiguous vec-id block; every vec is inserted as an ordinary HNSW node while two mappings remember doc ownership (map for reads, bucket for restarts). Search unions per-vector top-k results into doc candidates, then scores docs by sum-of-min-distances (late interaction) with a worker pool that respects a per-query concurrency budget. `ContainsDoc`/deletes treat ANY tombstoned sibling vec as doc-deleted.
**Invariant:** Skipping the purge turns a retried failed batch into orphaned duplicate vec-ids forever reachable by search. The `_mv_mappings` bucket write happens BEFORE `addOne` so a crash mid-doc leaves mappings consistent with inserted nodes. In `computeScore` the multivec distancer is DOT PRODUCT (`multiDistancerProvider = NewDotProductProvider()`, index.go :439) regardless of the index's main distance — sum-of-min is a similarity, not a distance.
**Probe:** `grep -c 'docIDVectors' adapters/repos/db/vector/hnsw/insert.go` → 2 (AddMultiBatch purge scan + mapping append; other uses live in search.go/delete.go/index.go); recovery-order test `lsmkv/recover_from_wal_order_integration_test.go::TestReplaceStrategy_RecoverFromMultipleWALs_NewestWins` (:32) pins the underlying store semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "AddMultiBatch", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual id-space mapping + purge-on-retry + budgeted late-interaction scoring. Adapt the mapping persistence to your KV. Omit muvera projection unless porting that mode too.
