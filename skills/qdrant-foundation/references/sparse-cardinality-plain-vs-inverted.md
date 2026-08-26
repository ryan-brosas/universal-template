<!-- capsule-v2 -->
# Sparse filtered search dispatch — when does the sparse engine iterate plainly instead of using the inverted index?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** For a filtered sparse-vector search, what chooses plain iteration vs inverted-index traversal, and how is the prefiltered set shared across a query batch?

## Cardinality-gated sparse dispatch with batch-wide prefilter cache
**Path/Symbol:** `lib/segment/src/index/sparse_index/sparse_vector_index/read_view/search.rs`: `search` (:33-68, batch entry + IDF remap), `get_query_cardinality` (:82-96), `search_scored` (:99-151), `search_plain` (:153-207), `search_sparse` (:210-256), `search_nearest_query` (:258-300), `search_query` (:302-342).
**Signature:** `fn search(&self, vectors: &[&QueryVector], filter: Option<&Filter>, top: usize, ctx: &VectorQueryContext) -> OperationResult<Vec<Vec<ScoredPointOffset>>>`; dispatch `if query_cardinality.max < threshold { search_plain } else { search_sparse }`.
**Data Shape:** `prefiltered_points: &mut Option<Vec<PointOffsetType>>` threaded through all calls of one batch; threshold = `config.full_scan_threshold.unwrap_or(DEFAULT_SPARSE_FULL_SCAN_THRESHOLD)`.

### Decisive source
```rust
Some(filter) => {
    // if cardinality is small - use plain search
    let query_cardinality = self.get_query_cardinality(filter, &hw)?;  // estimate + adjust_to_available_vectors
    let threshold = self.config.full_scan_threshold.unwrap_or(DEFAULT_SPARSE_FULL_SCAN_THRESHOLD);
    if query_cardinality.max < threshold {          // NOTE: .max, pessimistic bound
        self.search_plain(vector, filter, top, prefiltered_points, ctx)
    } else {
        self.search_sparse(vector, Some(filter), top, ctx)  // inverted index + filter_context per point
    }
}
```
Prefilter sharing:
```rust
let filtered_points = match prefiltered_points {
    Some(filtered_points) => filtered_points.iter().copied(),   // reuse: computed once for whole batch
    None => {
        let filtered_points = self.payload_index.query_points(filter, &hw_counter, &is_stopped)?;
        *prefiltered_points = Some(filtered_points);
        prefiltered_points.as_ref().unwrap().iter().copied()
    }
};
```
Non-vector queries bypass the index entirely (`search_scored`): raw `BatchFilteredSearcher.peek_top_iter(filtered_points)`.

**Flow:** batch loop clones-and-remaps IDF weights once per vector when `query_context.is_require_idf()` → per vector: empty vector → `[]`; top==0 → `[]`; Nearest → cardinality gate above; Recommend/Discover/Context/Feedback → always `search_scored` plain scorer over prefiltered ids (telemetry buckets: small_cardinality / filtered_sparse / unfiltered_sparse / filtered_plain / unfiltered_plain) → `search_plain` re-checks not-deleted on cached ids; `search_sparse` builds a combined closure `not_deleted(idx) && filter_context.check_infallible(idx)` and pushes it into `SearchContext::search`.
**Invariant:** (1) dispatch uses cardinality **max** — the pessimistic upper bound must clear the threshold before paying inverted-index overhead, opposite polarity from HNSW's exp-based selectivity; (2) `prefiltered_points` caches visible points only — consumers in the `Some` branch MUST NOT re-filter deferred/deleted (both call sites document this); (3) IO telemetry multiplier is set to 1 only when the index is on-disk (`hw_counter.set_vector_io_read_multiplier`), else 0; (4) non-Nearest queries never touch the inverted index even unfiltered.

**Probe:** `grep -c prefiltered_points lib/segment/src/index/sparse_index/sparse_vector_index/read_view/search.rs` → prints `18`. Direct test: `lib/segment/tests/integration/sparse_vector_index_search_tests.rs::sparse_vector_index_ram_filtered_search` (:371) plus parametric `compare_sparse_vectors_search_with_without_filter(full_scan_threshold)` (:68).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "search_nearest_query full_scan_threshold query_cardinality SearchContext plain_search peek_top_iter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt max-vs-threshold dispatch, the shared-prefilter contract (visible-only, no re-filtering), and non-Nearest→plain routing. Adapt SearchContext scratch pooling. Omit mmap/compressed inverted-index backends when porting just the dispatcher.
