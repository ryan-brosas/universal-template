<!-- capsule-v2 -->
# Facet value search — how does facet-search autocomplete merge typo'd normalized hits back to originals?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does `SearchForFacetValues` resolve a user query to original facet values, and where do typo rules and the two collection orders diverge?

## SearchForFacetValues.inner_execute
**Path/Symbol:** `crates/milli/src/search/facet/search.rs:SearchForFacetValues` (`execute` :75-117, `inner_execute` :119-221, `fetch_original_facets_using_normalized` :223-264) + `normalize_facet_string` (:354-373).
**Signature:** `pub fn execute(&self, candidates: &RoaringBitmap) -> Result<(Vec<FacetValueHit>, OrderBy)>`; `fn inner_execute(&self, fid, fst: fst::Set<&[u8]>, search_candidates: &RoaringBitmap, order: OrderBy) -> Result<ValuesCollection>`.
**Data Shape:** `DEFAULT_MAX_NUMBER_OF_VALUES_PER_FACET = 100` (:20); results are `(value=original_string, count)`; collection = Lexicographic Vec (fills then BREAKS) vs Count BinaryHeap<Reverse> (evicts worst).

### Decisive source
```rust
// search.rs:141-164 — the SAME typo ladder as the main query engine, but is_prefix=true
if authorize_typos && field_authorizes_typos {
    let exact_words_fst = index.exact_words(rtxn)?;
    if exact_words_fst.is_some_and(|fst| fst.contains(query)) {
        if fst.contains(query) { /* exact fetch only */ }
    } else {
        let one_typo = index.min_word_len_one_typo(rtxn)?;
        let two_typos = index.min_word_len_two_typos(rtxn)?;
        let is_prefix = true;
        let automaton = if query.len() < one_typo as usize {
            build_dfa(query, 0, is_prefix)
        } else if query.len() < two_typos as usize { build_dfa(query, 1, is_prefix) }
        else { build_dfa(query, 2, is_prefix) };
```
```rust
// search.rs:311-320 — lexicographic mode STOPS at max_values (prefix semantics)
ValuesCollection::Lexicographic { max, content } => {
    if content.len() < *max {
        content.push(value);
        if content.len() < *max { return ControlFlow::Continue(()); }
    }
    ControlFlow::Break(())
}
```

**Flow:** Validate the field is facet-searchable under the filterable-attributes rules (else `InvalidFacetSearchFacetName` with valid patterns + hidden fields + rule index); load the per-field FST of NORMALIZED values; with a query: normalize it (charabia lossy, single-explicit-locale skips detection), then either exact-FST fetch, DFA(0/1/2 typos, prefix) stream over the FST, or plain `Str::starts_with` when typos unauthorized; each normalized hit goes through `fetch_original_facets_using_normalized`: normalized→set-of-originals DB → level-0 bitmap per original → count = `search_candidates.intersection_len(bitmap)` → ONE original display value via `field_id_docid_facet_strings[(fid, any_docid, original)]`. Without a query: plain level-0 prefix walk. Counts-mode keeps the best-N via reversed max-heap; lexicographic mode stops early — FST order guarantees the first N ARE the lexicographically smallest.
**Invariant:** (1) Returned `value` must be an ORIGINAL string (display form), never the normalized lemma; fallbacks degrade to the normalized value with a logged error, never a panic; (2) missing normalized→original rows log-and-skip (`error!` + Continue), they don't fail the request; (3) Count mode NEVER breaks insertion (heap eviction), Lexicographic DOES — conflating them changes result completeness.
**Probe:** `crates/milli/src/search/facet/search.rs` tests module + integration `crates/meilisearch/tests/search/facet_search.rs` (typo + normalization cases). GREEN at pin (executed this pass via `cargo test -p milli --lib -- facet`, which includes this module's tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "SearchForFacetValues inner_execute fetch_original_facets_using_normalized", limit: 10 });
```

## Verdict
Adopt the normalized-FST + DFA-prefix ladder and the dual collection semantics; adapt charabia normalization to host tokenizers; omit the meilisearch HTTP route wiring.
