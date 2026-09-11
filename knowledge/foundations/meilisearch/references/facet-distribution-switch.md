<!-- capsule-v2 -->
# Facet distribution algorithm switch — when do you count per-document vs walk the levels?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What candidate threshold flips facet distribution from per-document counting to level-tree iteration, and why are strings special-cased?

## FacetDistribution.facet_values
**Path/Symbol:** `crates/milli/src/search/facet/facet_distribution.rs:FacetDistribution` (`facet_values` :255-296, `facet_distribution_from_documents` :110-177, `facet_numbers_distribution_from_facet_levels` :181-208, `facet_strings_distribution_from_facet_levels` :210-253, `select_field` :360-379) + `crates/milli/src/search/facet/facet_distribution_iter.rs` (`count_iterate_over_facet_distribution` :48-143, `LexicographicFacetDistribution` :146-232).
**Signature:** `fn facet_values(&self, field_id: FieldId, order_by: OrderBy) -> heed::Result<IndexMap<String, u64>>`; threshold constant `CANDIDATES_THRESHOLD: u64 = 3000` (:32).
**Data Shape:** Output preserves INSERTION order (IndexMap); per-doc path counts into a BTreeMap keyed by normalized value keeping the FIRST original; level path inserts original strings directly with a ControlFlow break at `max_values_per_facet`.

### Decisive source
```rust
// facet_distribution.rs:263-269 — the switch, and WHY strings always go per-doc below threshold
match (order_by, &self.candidates) {
    (OrderBy::Lexicographic, Some(cnd)) if cnd.len() <= CANDIDATES_THRESHOLD => {
        // Classic search, candidates were specified ... We also enter here for facet strings for performance reasons.
        self.facet_distribution_from_documents(field_id, Number, cnd, &mut distribution)?;
        self.facet_distribution_from_documents(field_id, String, cnd, &mut distribution)?;
    }
    _ => { /* numbers-then-strings via level iterators */ }
}
```
```rust
// facet_distribution_iter.rs:61-73 — Count mode's heap entry: count DESC, then DEEPEST level first
struct LevelEntry<'t> {
    count: u64,
    level: Reverse<u8>,   // BinaryHeap pops smallest ⇒ Reverse makes level 0 pop first
    left_bound: &'t [u8],
    group_size: u8,
    any_docid: u32,
}
```

**Flow:** ≤3000 candidates AND lexicographic AND explicit candidates ⇒ prefix-walk each candidate doc's `(field_id, docid)` facet entries and count them (strings aggregate under NORMALIZED keys keeping one original). Otherwise iterate the level tree: lexicographic recursion descends depth-first yielding values in order; COUNT mode pushes every intersecting group into a BinaryHeap ordered by (count desc, deepest-level-first) so highest-count values surface first while level-0 leaves pop before their ancestors' stale higher-level duplicates. Strings on the level path resolve each normalized value back to an original via `field_id_docid_facet_strings[(fid, any_docid, key)]`. Both stop at `max_values_per_facet`.
**Invariant:** (1) The 3000 threshold exists because per-doc counting is O(candidates × facets-per-doc) — cheap for small sets but quadratic-feeling beyond; porters who keep only one path get either slow or wrong-count distributions; (2) Count-mode ordering is (count, then Reverse(level)) — dropping the level tiebreaker yields ancestor-group double counts; (3) `any_docid` may be ANY document having the value (not necessarily a candidate) — it only feeds original-string lookup.
**Probe:** `facet_distribution.rs` tests `few_candidates_few_facet_values` (:447+) and the count/lexicographic suites in the same file; `facet_distribution_iter.rs` tests `filter_distribution_all` (:247-269) + `filter_distribution_all_stop_early` (:271-300). GREEN at pin (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "FacetDistribution facet_values CANDIDATES_THRESHOLD facet_distribution_from_documents", limit: 10 });
```

## Verdict
Adopt the dual-path threshold and the count-heap level discipline; adapt the IndexMap insertion-order guarantee if host output is unordered; omit meilisearch's facets-by-name routing (`select_field` legacy pattern matching).
