<!-- capsule-v2 -->
# Query cost model — how does the engine estimate how many similarity comparisons a query costs per point?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** How is a query's relative execution cost derived for rate limiting / planning, per query type?

## Per-query similarity-cost accounting
**Path/Symbol:** `lib/shard/src/query/query_enum.rs`: `QueryEnum::search_cost` (:90-103) + `fn search_cost` helper (:106-111), `is_distance_scored` (:31-40); `operation_rate_cost.rs` consumes such costs shard-wide.
**Signature:** `pub fn search_cost(&self) -> usize` delegating to `VectorInternal::similarity_cost` summed over the query's flat vector set.
**Data Shape:** input: query variant + its vectors (NamedQuery or multi-vector reco/discover/context/feedback queries via `flat_iter()`); output: usize ≈ "similarity comparisons this query will make against one point".

### Decisive source
```rust
/// Returns the estimated cost of using this query in terms of number of vectors.
/// The cost approximates how many similarity comparisons this query will make against one point.
pub fn search_cost(&self) -> usize {
    match self {
        QueryEnum::Nearest(named_query) => search_cost([&named_query.query]),
        QueryEnum::RecommendBestScore(named_query) => search_cost(named_query.query.flat_iter()),
        // ... RecommendSumScores / Discover / Context / FeedbackNaive identical
    }
}
fn search_cost<'a>(vectors: impl IntoIterator<Item = &'a VectorInternal>) -> usize {
    vectors.into_iter().map(VectorInternal::similarity_cost).sum()
}
```

**Flow:** each scoring request → enumerate ALL vectors it will compare against (flat over nested structures) → sum per-vector similarity costs → feeds `SearchRateCost`/load-profile accounting so multi-vector queries are charged proportionally, not as one unit.
**Invariant:** (1) only Nearest is distance-scored (`is_distance_scored`) — every other variant returns scores by construction and orders LargeBetter; (2) cost is per-POINT comparison count, independent of segment size; (3) sparse/dense/multi-dense contribute through one uniform `similarity_cost`, keeping rate limits fair across vector types.

**Probe:** `grep -c similarity_cost lib/shard/src/query/query_enum.rs` → prints `1` (the single `.map(VectorInternal::similarity_cost)` in the shared helper; every variant routes through it). Coverage caveat: pinned indirectly by rate-limit tests (`lib/shard/src/operation_rate_cost.rs` consumers), not by a direct unit on search_cost.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "search_cost similarity_cost flat_iter operation_rate_cost SearchRateCost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flat-sum cost definition. Adapt similarity_cost weights to host distance kernels. Omit gRPC/rest conversion plumbing.
