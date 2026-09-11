<!-- capsule-v2 -->
# Query graph — the DAG of every way to read a query

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How is one user query turned into a graph of alternative interpretations (ngrams, positions), and how are nodes removed for word-dropping without breaking paths?

## QueryGraph with wrapping positions and ngram fan-out
**Path/Symbol:** `crates/milli/src/search/new/query_graph.rs:QueryGraph::from_query` (:96-187), `build_initial_edges` (:254-301), `remove_nodes_keep_edges` (:190-210), `removal_order_for_terms_matching_strategy_last` (:346-377), `removal_order_for_terms_matching_strategy_frequency` (:303-344), `removal_order_for_terms_matching_strategy` (:379-406).
**Signature:** `pub fn from_query(ctx, tokenizer, terms: &[LocatedQueryTerm]) -> Result<(QueryGraph, Vec<LocatedQueryTerm>)>`
**Data Shape:** Nodes = `QueryNode { data: Term(LocatedQueryTermSubset) | Deleted | Start | End, predecessors/successors: SmallBitmap<QueryNode> }`. Each term node carries `positions: RangeInclusive<u16>` and `term_ids: RangeInclusive<u8>`; ngram nodes carry the span of their components (e.g. 2-gram ⇒ term_ids i..=i+1). Returns the graph AND an extended term list including synthesized ngram terms.

### Decisive source
```rust
// hard separator advances position by 7 (parse_query.rs:116-119), so
// "hello -world" puts -world far away; position starts at u16::MAX and
// wraps to 0 on the first token:
position = position.wrapping_add(1);
...
if !prev1.is_empty() {
    if let Some(ngram) = query_term::make_ngram(ctx, tokenizer, &terms[term_idx-1..=term_idx], &nbr_typos)? {
        // ngram node added alongside its component words' nodes
    }
}
```

**Flow:** For each parsed term add its node, then try 2-grams and 3-grams over consecutive positions (make_ngram refuses phrases, non-consecutive positions, >MAX_WORD_LENGTH joins, and grants the ngram `allowed_typos(ngram) − (n−1)`). After all nodes exist, `build_initial_edges` wires each node to successors whose term_ids.start is strictly greater than its own end, keeping ONLY the minimal next start tier. Word dropping = remove_nodes_keep_edges (preds→succs shortcut, node marked Deleted); simplify() then iteratively drops disconnected nodes.
**Invariant:** (1) Position counter uses `wrapping_add` — starting at u16::MAX so the first token lands at position 0; a hard separator jumps +7 to encode phrase boundaries into positions. (2) The removal-order ladders never emit the LAST group: `res.pop()` when no mandatory term exists — one interpretation must always survive. Frequency strategy orders terms by document frequency ascending (rarest dropped first, zero-frequency = u64::MAX cost); Last strategy ranks `1 + last_term_idx − term_idx`. Phrases and mandatory terms are never droppable.
**Probe:** `crates/milli/tests/search/typo_tolerance.rs:test_typo_tolerance_one_typo` (:19-96) exercises end-to-end graph search with typo derivations; `src/search/new/query_term/parse_query.rs:start_with_hard_separator` (:386-406) pins the wrapping-position behavior (#3785 regression: "attempt to add with overflow" before the fix). All GREEN at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "build_initial_edges", limit: 5 });
```

## Verdict
Adopt the DAG-of-readings construction, minimal-next-tier edge building, and prefix-preserving deletion; adapt node storage to host containers; omit the SmallBitmap bit-packing internals if the host has its own compact set.
