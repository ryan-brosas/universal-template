<!-- capsule-v2 -->
# Bucket sort — the recursive ranking-rule executor

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How do N ranking rules cooperate to produce one ordered page, and where do offset/threshold/distinct/degraded semantics live that a naive port gets wrong?

## Nested bucket iteration with back!() control flow
**Path/Symbol:** `crates/milli/src/search/new/bucket_sort.rs:bucket_sort` (:23-343), `maybe_add_to_results` (:388-466), `inject_pins` (:349-383); rule contract `ranking_rules.rs:RankingRule` (:37-88).
**Signature:** `pub fn bucket_sort<'ctx, Q: RankingRuleQueryTrait>(ctx, ranking_rules: Vec<BoxRankingRule<'ctx, Q>>, query: &Q, distinct, universe, from, length, scoring_strategy, logger, deadline, ranking_score_threshold, exhaustive_number_hits, max_total_hits, pins) -> Result<BucketSortOutput>`
**Data Shape:** Each `next_bucket` returns `RankingRuleOutput { query: Q (child's query — the graph shrinks to used subgraph), candidates: RoaringBitmap, score: ScoreDetails }`; per-rule universes tracked in `ranking_rule_universes[depth]`.

### Decisive source
```rust
while valid_docids.len() < max_len_to_evaluate {
    if ranking_rule_universes[cur].is_empty()
        || (scoring_strategy == ScoringStrategy::Skip && ...len() == 1) { back!(); continue; }
    // deadline exceeded ⇒ degrade via non_blocking_next_bucket:
    if deadline.exceeded() { loop { match rules[cur].non_blocking_next_bucket(...) {
        Poll::Pending => { /* push ScoreDetails::Skipped, drain bucket wholesale,
                             pop back toward root, return degraded:true at depth 0 */ }
        ...
    }}}
    ...
    if cur == rules_len - 1 || skip && bucket <= 1 || cur_offset + len < ranked_from || below_threshold {
        maybe_add_to_results!(candidates); ranking_rule_scores.pop(); continue;
    }
    cur += 1; universes[cur] = candidates.clone(); rules[cur].start_iteration(ctx, ..., &candidates, &bucket.query, ...)?;
}
```

**Flow:** Depth-first over rule indices: rule i partitions its universe into score buckets; each bucket becomes rule i+1's universe AND its new query (the graph restricted to conditions actually used). Terminal rule or single-candidate buckets are flushed to results. Distinct is applied at flush time and excludes survivors from every pending universe. Below-threshold buckets are removed from all_candidates so estimatedTotalHits stays honest.
**Invariant:** (1) A child's `start_iteration` receives the PARENT'S BUCKET as universe and the parent's `query` output — scores compose as a stack (`ranking_rule_scores`), popped on back; (2) `all_candidates` must include skipped-for-offset and excluded-by-distinct docs (estimates!), but NOT threshold-discarded ones — the comment "this **must** be done **after** writing the entire results in `all_candidates`" (:83-85) pins drain-after-union ordering; (3) pins (pinned docs) reroute the whole page: with pins, organic window becomes `(0, from+length)` and inject_pins merges by position afterward, pumping pins forward when organic results run short; (4) deadline exhaustion returns `degraded: true`, never partial ordering.
**Probe:** `crates/milli/src/search/new/tests/cutoff.rs:degraded_search_and_score_details` (:99+) pins degraded output shape with score details under cutoff; `test_typo_bucketing` in typo.rs pins multi-rule bucket composition (Words then Typo). GREEN at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "bucket_sort", limit: 5 });
```

## Verdict
Adopt the recursive-bucket executor shape (query-shrinking + score-stack + estimate-honest all_candidates); adapt pin injection only if the host has pinned docs; omit logger plumbing. Direct tests exist upstream and pass at HEAD.
