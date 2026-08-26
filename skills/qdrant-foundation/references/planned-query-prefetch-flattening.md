<!-- capsule-v2 -->
# PlannedQuery prefetch flattening — how does a nested prefetch tree become batched segment searches with staged rescoring?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** How are recursive `ShardPrefetch`es flattened into indexed search/scroll lists, and where does each scoring query execute (shard vs collection)?

## Flatten to leaf batches + MergePlan tree
**Path/Symbol:** `lib/shard/src/query/planned_query.rs`: struct `PlannedQuery{root_plans, searches, scrolls}` (:17-29), `MergePlan`/`Source`/`RescoreStages` (:38-103), `add` + MAX_PREFETCH_DEPTH=64 (:110-172), `root_plan_with_prefetches` (:220-298), `recurse_prefetches` (:306-366), `leaf_source_from_scoring_query` (:372-478).
**Signature:** `fn recurse_prefetches(core_searches: &mut Vec<CoreSearchRequest>, scrolls: &mut Vec<QueryScrollRequestInternal>, prefetches: Vec<ShardPrefetch>, propagate_filter: &Option<Filter>) -> OperationResult<Vec<Source>>`.
**Data Shape:** `Source::SearchesIdx(usize)` / `ScrollsIdx(usize)` reference the flat batches; `Source::Prefetch(Box<MergePlan>)` nests; `RescoreStages{shard_level, collection_level}` both optional.

### Decisive source
```rust
// Filters are propagated into the leaves
let filter = Filter::merge_opts(propagate_filter.clone(), filter);
// nested fusion executes at SHARD level because inner results must be materialized first:
// Even if this is a fusion request, it can only be executed at shard level here,
// because we can't forward the inner results to the collection level without materializing them.
let rescore_stages = RescoreStages::shard_level(RescoreParams { rescore, limit, score_threshold, params });
```
Root-level staging:
```rust
rescore @ (ScoringQuery::Vector(_) | OrderBy | Formula | Sample) => RescoreStages::shard_level(...),
ScoringQuery::Fusion(f) => RescoreStages::collection_level(RescoreParams { rescore: Fusion(f), ... }),
ScoringQuery::Mmr(mmr) => RescoreStages {
    // shard stage: plain Nearest rescore down to candidates_limit
    shard_level: Some(RescoreParams { rescore: Nearest(vector, using), limit: candidates_limit, .. }),
    collection_level: Some(RescoreParams { rescore: Mmr(mmr), limit, .. }),   // MMR itself at collection
},
```
Leaf legality:
```rust
Some(ScoringQuery::Fusion(_)) => return Err(validation_error("cannot apply Fusion without prefetches")),
Some(ScoringQuery::Formula(_)) => return Err(validation_error("cannot apply Formula without prefetches")),
```

**Flow:** depth-check (≤64) → limit += offset (saturating; pinned for usize::MAX overflow) → no-prefetch root: single source, only MMR gets a collection-stage → with-prefetch root: recurse tree, parent filters merge into children (`Filter::merge_opts`), leaves become CoreSearchRequests (Vector/MMR-candidates, offset forced 0, vectors/payloads stripped) or scroll requests (OrderBy/Random/None), every non-leaf node gets its rescore stage → MMR splits into two stages as above.
**Invariant:** (1) Fusion is NEVER legal as a leaf and NEVER runs at collection level when nested — materialization forces shard level; (2) leaf searches always carry `offset: 0` and `with_vector/payload = false` — payloads/vectors attach once at the root after merging; (3) filter propagation is parent→child only, never sibling→sibling; (4) depth guard fires BEFORE any flattening work; (5) `prefetches_depth()` counts nodes, so depth 65 errors while 64 passes (pinned).

**Probe:** `grep -c "PlannedQuery::try_from" lib/shard/src/query/tests.rs` → prints `9`. Direct tests: `test_try_from_double_rescore` (:16), `test_try_from_limit_offset_saturates_on_overflow` (:130), `test_try_from_hybrid_query` (:207), `test_try_from_rrf_without_source` (:318), `test_detect_max_depth` (:463, pins 64 ok / 65 err via `make_prefetches_at_depth`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "PlannedQuery MergePlan RescoreStages recurse_prefetches leaf_source_from_scoring_query", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flattening shape, filter propagation, staging rules (vector-family→shard, fusion-root→collection, nested-fusion→shard, MMR split). Adapt request types to host API. Omit gRPC conversion layers (`conversions.rs`).
