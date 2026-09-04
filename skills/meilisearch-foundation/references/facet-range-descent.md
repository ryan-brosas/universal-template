<!-- capsule-v2 -->
# Facet range search descent — when can a filter take a whole subtree's bitmap without recursing?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What exact boundary conditions decide skip / stop / take-whole-group / recurse at every level of the facet tree during a range filter?

## FacetRangeSearch.run
**Path/Symbol:** `crates/milli/src/search/facet/facet_range_search.rs` (`find_docids_of_facet_within_bounds` :15-67, `run_level_0` :83-126, `run` :147-331).
**Signature:** `pub fn find_docids_of_facet_within_bounds<'t, BoundCodec>(rtxn, db, field_id: u16, left: &Bound<EItem>, right: &Bound<EItem>, universe: Option<&RoaringBitmap>, docids: &mut RoaringBitmap) -> Result<()>`.
**Data Shape:** Bounds are byte-encoded `Bound<&[u8]>`; `universe` enables LAZY decode (`FacetGroupLazyValueCodec` + `intersection_with_serialized`) so bitmaps are only materialized intersected with candidates; entry always starts at `(highest_level, first_value_of_field, Included(last_value), usize::MAX)`.

### Decisive source
```rust
// facet_range_search.rs:172-183 — skip compares against the NEXT key's bound,
// because an element's implicit range is [own.left_bound .. next.left_bound)
let should_skip = {
    match self.left {
        Bound::Included(left) => left >= next_key.left_bound,
        Bound::Excluded(left) => left >= next_key.left_bound,
        Bound::Unbounded => false,
    }
};

// facet_range_search.rs:199-211 — whole-group test needs BOTH conditions
let should_take_whole_group = {
    let left_condition = match self.left {
        Bound::Included(left) => previous_key.left_bound >= left,
        Bound::Excluded(left) => previous_key.left_bound > left,
        Bound::Unbounded => true,
    };
    let right_condition = match self.right {
        Bound::Included(right) => next_key.left_bound <= right,
        ...
    };
    left_condition && right_condition
};
```
And the tail case (:275-310) repeats the right-condition four ways over `(self.right, rightmost_bound)` — `Included/Included ⇒ rightmost <= right`, `Excluded/Included ⇒ rightmost < right`, etc.

**Flow:** From the top level, iterate the level slice keeping `previous = (key,value)` one behind `next`: (1) SKIP while the search's left bound has passed `next_key.left_bound` (previous' whole implicit range is left of the query); (2) STOP when the query's right bound is below `previous_key.left_bound`; (3) TAKE-WHOLE-GROUP — OR the group's bitmap into `docids` WITHOUT recursing — exactly when previous' implicit range `[previous.left_bound, next.left_bound)` fits inside the query bounds; (4) otherwise RECURSE into previous' children (`level-1`, `starting=previous.left_bound`, `rightmost=Excluded(next.left_bound)`, `group_size=previous.size`). Level 0 instead checks each single value against `RangeBounds::contains`. The final element after the loop is adjudicated separately using `rightmost_bound` (usize::MAX group at top ⇒ field-id check guards overrun).
**Invariant:** (1) A node's range is IMPLICIT — `[own.left_bound, next_sibling.left_bound)` — so every comparison must use the NEXT key; using own bounds silently mis-classifies boundary values; (2) take-whole-group requires the ENTIRE subtree inside bounds; partial overlap must recurse; (3) universe-intersected lazy decode means returned docids are already candidate-filtered.
**Probe:** `crates/milli/src/search/facet/facet_range_search_test.rs` — `filter_range_increasing` (:39-91), `filter_range_decreasing` (:92-149), `filter_range_pinch` (:150-216), `filter_range_unbounded` (:217-303), `filter_range_exact` (:304+) snapshot all four decisions across simple + random indexes. GREEN at pin (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "find_docids_of_facet_within_bounds FacetRangeSearch run", limit: 10 });
```

## Verdict
Adopt the four-way decision ladder and the implicit-range/next-key comparison rule; adapt bound encoding to host ordering; omit the cellulite geojson twin branches in `index_filter.rs` that call this function.
