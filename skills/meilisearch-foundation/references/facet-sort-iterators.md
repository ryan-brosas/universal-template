<!-- capsule-v2 -->
# Facet sort iterator — how do you stream candidates ordered by a facet value with each doc emitted once?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How do the ascending/descending facet sorts walk the level tree lazily, and what does the descending twin track that ascending doesn't?

## AscendingFacetSort / DescendingFacetSort
**Path/Symbol:** `crates/milli/src/search/facet/facet_sort_ascending.rs` (`ascending_facet_sort` :32-52, `AscendingFacetSort::next` :65-113); `crates/milli/src/search/facet/facet_sort_descending.rs` (`descending_facet_sort` :15-36, `DescendingFacetSort::next` :52-118).
**Signature:** `pub fn ascending_facet_sort<'t>(rtxn, db, field_id: u16, candidates: RoaringBitmap) -> Result<impl Iterator<Item = Result<(RoaringBitmap, &'t [u8])>>>` (descending twin same shape).
**Data Shape:** Stack of `(remaining_candidates, level-range-iterator[, right_bound])`; yields `(bitmap, exact_left_bound)` per distinct facet value; docids are REMOVED from remaining as emitted so multi-valued docs surface under their smallest (or largest) value only.

### Decisive source
```rust
// facet_sort_ascending.rs:91-108 — intersect, subtract, descend or yield
bitmap &= &*documents_ids;
if !bitmap.is_empty() {
    *documents_ids -= &bitmap;
    if level == 0 {
        return Some(Ok((bitmap, left_bound)));   // exact value
    }
    let starting_key_below = FacetGroupKey { field_id: self.field_id, level: level - 1, left_bound };
    let iter = ... .take(group_size as usize);
    self.stack.push((bitmap, iter));
    continue 'outer;
}

// facet_sort_descending.rs:86-100 — the extra state ascending doesn't need
let end_key_kelow = match *right_bound {
    Bound::Included(right) => Bound::Included(FacetGroupKey { field_id, level: level - 1, left_bound: right }),
    Bound::Excluded(right) => Bound::Excluded(...),
    Bound::Unbounded => Bound::Unbounded,
};
let prev_right_bound = *right_bound;
*right_bound = Bound::Excluded(left_bound);
```

**Flow:** Both start from `(candidates, iterator-at-highest-level)`; each `next()` pops nothing while progress is made: intersect group bitmap with remaining candidates; empty ⇒ this subtree exhausted after deeper pops (`documents_ids.is_empty()` breaks to stack pop); non-empty ⇒ subtract from remaining and either YIELD at level 0 or push a child iterator bounded by the parent's `size`. Descending additionally carries a per-frame `right_bound` (initialized `Included(last_value)`) that becomes the rev-range's upper end for child iterators and is narrowed to `Excluded(left_bound)` as it advances — without it, reverse iteration would re-enter groups already consumed by a right neighbor. Field-id overrun terminates iteration (`field_id != self.field_id ⇒ None`).
**Invariant:** (1) Every document appears in exactly ONE yielded group per traversal (subtract-before-descend); (2) yielded bound at level 0 IS the facet value (left_bound = exact value); (3) the descending right-bound narrowing is load-bearing — porting it as plain `rev_range(..=first_key)` duplicates groups.
**Probe:** `facet_sort_ascending.rs` tests `filter_sort_ascending` (:128-145), `filter_sort_ascending_multiple_field_ids` (:147-176), no-candidates/inexisting-field-id empties (:178-229); `facet_sort_descending.rs` tests mirror them (:136-243). GREEN at pin (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "ascending_facet_sort AscendingFacetSort stack", limit: 10 });
```

## Verdict
Adopt the lazy stack-machine with subtract-on-emit; adapt iterator types to host KV range API; omit the itertools Either wrapper plumbing.
