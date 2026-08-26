<!-- capsule-v2 -->
# Ranking-rule assembly — how settings criteria become the rule pipeline

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** Given user-configured ranking rules, which concrete rule objects are instantiated, in what order, and what silent coercions happen that a porter must reproduce?

## get_ranking_rules_for_query_graph_search
**Path/Symbol:** `crates/milli/src/search/new/mod.rs:get_ranking_rules_for_query_graph_search` (:510-649), `resolve_sort_criteria` (:651-716), placeholder twin (:353-416), vector twin (:419-507), `Criterion` enum `crates/milli/src/criterion.rs` (:26-56).
**Signature:** `fn get_ranking_rules_for_query_graph_search<'ctx>(ctx, sort_criteria: &Option<Vec<AscDesc>>, geo_param, terms_matching_strategy) -> Result<Vec<BoxRankingRule<'ctx, QueryGraph>>>`
**Data Shape:** Returns boxed rules; each Criterion is instantiated AT MOST ONCE via local bool latches (words/typo/proximity/attribute/attribute_rank/word_position/exactness/sort + sorted_fields set).

### Decisive source
```rust
// Don't add the `words` ranking rule if the term matching strategy is `All`
if matches!(terms_matching_strategy, TermsMatchingStrategy::All) { words = true; }
for rr in settings_ranking_rules {
    // Add Words before any of: typo, proximity, attribute, attribute rank,
    // word position, exactness. Without this, placing one of the newer
    // `attributeRank`/`wordPosition` rules before `words` would skip the
    // word-dropping done by Words and silently return fewer hits.
    match rr {
        Typo | Attribute | AttributeRank | WordPosition | Proximity | Exactness => {
            if !words { ranking_rules.push(Box::new(Words::new(terms_matching_strategy))); words = true; }
        }
        _ => {}
    }
    ...
    Criterion::Attribute => { if attribute || attribute_rank || word_position { continue; }
        ranking_rules.push(Box::new(Fid::new(None)));
        ranking_rules.push(Box::new(Position::new(None))); }   // legacy = TWO graph rules
```

**Flow:** Settings criteria are walked in order; duplicates skipped; `Attribute` expands to Fid+Position pair (legacy semantics), while newer AttributeRank ⇒ Fid only and WordPosition ⇒ Position only; Exactness ⇒ ExactAttribute then Exactness; Sort ⇒ resolve_sort_criteria appends Sort/GeoSort per requested AscDesc (dedup by field); placeholder search DROPS all query-dependent rules; vector search replaces every query-dependent rule with ONE VectorSort at the first query-dependent slot.
**Invariant:** (1) The Words-first coercion is load-bearing for correctness (fewer hits otherwise) — it fires even when Words is absent from settings; with TermsMatchingStrategy::All, Words is pre-latched so it never runs (all terms mandatory); (2) rule identity is per-pipeline: a criterion listed twice in settings still yields one rule; (3) check_sort_criteria (:998-1051) rejects sort usage unless `Sort` is in settings AND fields are declared sortable — error BEFORE any search work.
**Probe:** `crates/milli/src/search/new/tests/typo.rs:test_typo_ranking_rule_not_preceded_by_words_ranking_rule` (:462-518) pins exactly the Words-injection coercion; GREEN at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "get_ranking_rules_for_query_graph_search", limit: 5 });
```

## Verdict
Adopt the settings→pipeline compiler including legacy expansions and the Words-first invariant; adapt rule inventory to host; omit AscDesc parsing internals.
