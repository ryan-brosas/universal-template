<!-- capsule-v2 -->
# ACORN selectivity dispatch — when does a filtered query switch from HNSW traversal to ACORN?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** How is the ACORN-vs-HNSW decision made per segment before any graph work starts?

## Selectivity-gated algorithm enum
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs`: `search_with_graph` (:30-179), ACORN block (:59-86); enum `SearchAlgorithm::{Hnsw, Acorn}` in `graph_layers.rs`; default `ACORN_MAX_SELECTIVITY_DEFAULT` in `types.rs`.
**Signature:** `fn search_with_graph(&self, vector: &QueryVector, filter: Option<&Filter>, top: usize, params: Option<&SearchParams>, custom_entry_points: Option<&[PointOffsetType]>, ctx: &VectorQueryContext) -> OperationResult<Vec<ScoredPointOffset>>`.
**Data Shape:** input: optional filter, `params.acorn: Option<AcornParams{enable, max_selectivity}>`; estimate inputs: `vector_storage.available_vector_count()`, `id_tracker.available_point_count()`, payload cardinality; output: algorithm choice consumed by `self.graph.search(top, ef, algorithm, ...)`.

### Decisive source
```rust
let mut algorithm = SearchAlgorithm::Hnsw;
if acorn_enabled && self.config.m0 != 0 && let Some(filter) = filter {
    // NOTE: technically we also might want to use ACORN for unfiltered
    // searches for segments with a lot of deleted points. ...
    let available_vector_count = self.vector_storage.available_vector_count();
    let selectivity = if available_vector_count == 0 { 1.0 } else {
        let query_point_cardinality = self.payload_index.estimate_cardinality(filter, &hw_counter)?;
        let query_cardinality = adjust_to_available_vectors(
            query_point_cardinality,
            available_vector_count,
            self.id_tracker.available_point_count(),
        );
        query_cardinality.exp as f64 / available_vector_count as f64
    };
    if selectivity <= acorn_max_selectivity { algorithm = SearchAlgorithm::Acorn; }
}
```

**Flow:** read user flags (`params.acorn.enable`, `max_selectivity`, default when absent) → require m0 ≠ 0 and a filter → estimate matched points (cardinality exp) adjusted to *available* (non-vector-deleted) vectors → selectivity = adjusted_exp / available_vectors (1.0 when empty) → if ≤ threshold pick `SearchAlgorithm::Acorn` else keep `Hnsw` → the chosen enum flows into `graph.search(oversampled_top, ef, algorithm, points_scorer, entry_points, &is_stopped)`.
**Invariant:** (1) the decision uses **exp**, not min/max — it is an expected-cost model, not a guarantee; (2) adjustment must use available VECTORS for the denominator but available POINTS for the deleted-correlation re-estimation — swapping them skews selectivity on partially-deleted segments; (3) ACORN requires m0>0 because it traverses only level 0; (4) unfiltered queries never take ACORN here even with heavy deletion (comment documents the deliberate omission); (5) empty segments report selectivity 1.0 (worst case) so they never route to ACORN.

**Probe:** `grep -c "acorn_max_selectivity" lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs` → prints `2`. Coverage caveat: no dedicated unit test pins this gate at this HEAD; strict-mode API tests (`tests/openapi/test_strictmode.py`) validate request-shape validation only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "SearchAlgorithm Acorn selectivity adjust_to_available_vectors acorn enable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-search selectivity gate and the exp/available-vectors ratio. Adapt threshold defaults and param plumbing to host SearchParams. Omit ACORN's level-0-only traversal internals if porting only the dispatcher.
