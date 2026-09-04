<!-- capsule-v2 -->
# Discover search two-stage entry — how does a Discover query bootstrap its own HNSW entry points?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** How does a Discover (pairs-based constrained) query get entry points into the HNSW graph before its real traversal?

## Context-search warmup feeding discover traversal
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs`: `discover_search_with_graph` (:314-349); batch router `search_vectors_with_graph` (:181-208) maps `QueryVector::Discover` here.
**Signature:** `fn discover_search_with_graph(&self, discover_query: DiscoverQuery<VectorInternal>, filter, top, params, ctx) -> OperationResult<Vec<ScoredPointOffset>>`.
**Data Shape:** stage 1 reuses the SAME filter/params with `DISCOVERY_ENTRY_POINT_COUNT = 10` as top; stage 2 passes those 10 ids via `custom_entry_points: Option<&[PointOffsetType]>`.

### Decisive source
```rust
// Stage 1: Find best entry points using Context search
let query_vector = QueryVector::Context(discover_query.pairs.clone().into());
const DISCOVERY_ENTRY_POINT_COUNT: usize = 10;
let custom_entry_points: Vec<_> = self.search_with_graph(
    &query_vector, filter, DISCOVERY_ENTRY_POINT_COUNT, params, None, ctx)?
    .iter().map(|x| x.idx).collect()?;
// Stage 2: Discover search with entry points
self.search_with_graph(&QueryVector::Discover(discover_query), filter, top, params,
    Some(&custom_entry_points), ctx)
```

**Flow:** pairs → Context query → filtered HNSW search for 10 candidates honoring user ef/params → their internal ids become explicit graph entries → Discover traversal starts from them instead of the default highest-level entry.
**Invariant:** (1) stage 2 receives NO default entry points — if stage 1 returns fewer than requested it still overrides the usual top-layer entry; (2) both stages share one filter context so stage-1 entries already satisfy the payload constraint; (3) `pairs.clone()` is required because stage 2 consumes the original discover_query.

**Probe:** `grep -c "DISCOVERY_ENTRY_POINT_COUNT" lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs` → prints `2`. Coverage caveat: behavior pinned indirectly through discover integration tests in `hnsw_discover_test.rs`; no unit names this helper.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "discover_search_with_graph custom_entry_points QueryVector Context pairs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-stage warmup and shared-filter entry seeding. Adapt the constant (10) to host tuning. Omit API-level discover parsing (`conversions.rs`, grpc try_context_pair_from_grpc).
