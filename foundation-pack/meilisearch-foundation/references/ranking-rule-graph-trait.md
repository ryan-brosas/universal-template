<!-- capsule-v2 -->
# Ranking-rule graph — per-rule condition DAG over the query graph

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does each ranking rule (typo/proximity/fid/position/exactness/words) encode its cost model as edges, and what is the porting contract of `RankingRuleGraphTrait`?

## RankingRuleGraph built by a 3-method trait
**Path/Symbol:** `crates/milli/src/search/new/ranking_rule_graph/mod.rs:RankingRuleGraphTrait` (:93-118), `RankingRuleGraph::build` in `build.rs` (:10-92), typo instantiation `ranking_rule_graph/typo/mod.rs:TypoGraph::build_edges` (:41-79).
**Signature:** `trait RankingRuleGraphTrait { type Condition; fn resolve_condition(ctx, condition, universe) -> Result<ComputedCondition>; fn build_edges(ctx, interner, source, dest) -> Result<Vec<(u32, Interned<Condition>)>>; fn rank_to_score(rank: Rank) -> ScoreDetails; }`
**Data Shape:** `Edge { source_node, dest_node, cost: u32, condition: Option<Interned<Condition>>, nodes_to_skip: SmallBitmap<QueryNode> }`. Conditions are deduped in a `DedupInterner`; edges live in a fixed-size store with per-node SmallBitmap index. Unconditional edges (`condition: None`) are skip-edges.

### Decisive source
```rust
// typo/mod.rs build_edges — ngrams carry a base typo cost:
let base_cost = if term.term_ids.len() == 1 { 0 } else { term.term_ids.len() as u32 };
for nbr_typos in 0..=term.term_subset.max_typo_cost(ctx) {
    let mut term = term.clone();
    match nbr_typos {
        0 => { term.term_subset.clear_one_typo_subset(); term.term_subset.clear_two_typo_subset(); }
        1 => { term.term_subset.clear_zero_typo_subset(); term.term_subset.clear_two_typo_subset(); }
        2 => { term.term_subset.clear_zero_typo_subset(); term.term_subset.clear_one_typo_subset(); }
        _ => panic!(),
    };
    edges.push((nbr_typos as u32 + base_cost,
        conditions_interner.insert(TypoCondition { term, nbr_typos })));
}
```

**Flow:** For every query-graph edge source→dest the builder emits (a) an optional skip-edge when a matching strategy priced ignoring dest (cost × dest term_ids len), then (b) rule-specific conditional edges from `build_edges`. The Typo rule emits one edge per allowed typo count with subsets cleared so each condition matches exactly its tier. Proximity emits costs right_ngram_max..MAX_DISTANCE−1+ngram_max plus an unconditional max-cost fallback; adjacent-position gaps become unconditional Term edges ("the sun .. are beautiful" after word removal has NO proximity between sun/are). Words emits exactly one zero-cost condition per term.
**Invariant:** Edge cost = f(rule semantics + ngram span); the same Condition value is deduped across edges via the interner, so removing "all edges with condition C" (remove_edges_with_condition) prunes the whole graph at once and returns affected source nodes for cost-table repair.
**Probe:** `crates/milli/src/search/new/tests/typo.rs:test_typo_bucketing` (:521-594) pins bucket ordering under criteria=[Typo] — documents ordered exact → 1-typo → split/ngram variants. GREEN at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "TypoCondition", limit: 5 });
```

## Verdict
Adopt the trait shape (build_edges / resolve_condition / rank_to_score) as the porting seam for any cost-graph ranking rule; adapt condition types per host rule set; omit roaring/score_details wiring details where the host differs.
