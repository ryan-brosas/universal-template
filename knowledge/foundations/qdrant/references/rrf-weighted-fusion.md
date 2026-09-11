<!-- capsule-v2 -->
# Weighted RRF fusion — how are heterogeneous prefetch result lists merged into one ranking?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** What is the exact per-position score formula, how do weights act, and what happens to input scores and ties?

## Weighted Reciprocal Rank Fusion
**Path/Symbol:** `lib/segment/src/common/reciprocal_rank_fusion.rs`: `DEFAULT_RRF_K=2` (:14), `position_score` (:32-39), `rrf_scoring` (:54-99); request-side enum `FusionInternal::Rrf{k, weights}` + `Dbsf` in `lib/shard/src/query/mod.rs` (:192-203).
**Signature:** `pub fn rrf_scoring(responses: Vec<Vec<ScoredPoint>>, k: usize, weights: Option<&[f32]>) -> OperationResult<Vec<ScoredPoint>>`; `fn position_score(position: usize, k: usize, weight: f32) -> f32`.
**Data Shape:** input: N ranked lists (lengths may differ) of ScoredPoint; only ORDER matters — incoming `.score` is discarded for fusion purposes and replaced by the accumulated rrf score; output: single descending list keyed by point id.

### Decisive source
```rust
// The formula is: 1.0 / ((position + 1)/weight + k - 1.0)
// With weight=1.0 (default): 1.0 / (position + k)
// weight=3.0 is equivalent to dividing the position by 3 ...
// (position + 1) accounts for 0-based indexing, so weight affects the top-ranked item too.
if weight <= 0.0 { return 0.0; }                    // negligible contribution, not an error
1.0 / ((position + 1) as f32 / weight + k as f32 - 1.0)

match points_by_id.entry(point.id) {
    Entry::Occupied(mut entry) => entry.get_mut().score += rrf_score,   // accumulate
    Entry::Vacant(entry)         => { point.score = rrf_score; entry.insert(point); }
}
scores.sort_unstable_by(|a,b| OrderedFloat(b.score).cmp(&OrderedFloat(a.score))); // does NOT break ties
```

**Flow:** validate `weights.len() == responses.len()` else validation error → zip each response with its weight → accumulate per-id scores in an AHashMap → collect, sort by score desc with `sort_unstable_by` (ties keep arbitrary order deliberately) → returned to shard layer as `ScoringQuery::Fusion` output. Positioning: fusion executes at COLLECTION level when it is the root query (`RescoreStages::collection_level`) but at SHARD level when nested under a prefetch (`planned_query.rs` :348-356 comment: inner results must be materialized first).
**Invariant:** (1) k default = 2 (not the literature-common 60) — top positions dominate; (2) weight divides POSITION, so a 3:1 weight ratio means "3 results of source A count like 1 of B" at equal rank; (3) zero/negative weights contribute exactly 0 rather than erroring; (4) original scores are overwritten on first sight and summed thereafter — never mix raw scores into fusion output; (5) tie order is unspecified by design.

**Probe:** `grep -c "fn test_rrf" lib/segment/src/common/reciprocal_rank_fusion.rs` → prints `7`. Direct tests: `test_rrf_scoring_one` (:126, pins score 1/(0+2)=0.5), `test_rrf_scoring` (:135, pins exact floats 1.0833334/0.8333334/0.5833334/0.5 across three lists), `test_rrf_scoring_weighted` (:175).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "rrf_scoring position_score DEFAULT_RRF_K FusionInternal weights", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the weighted formula verbatim including the +1/-1 bookkeeping and zero-weight rule. Adapt container types freely. Omit DBSF here (distribution-based fusion lives in the same enum but is a separate contract).
