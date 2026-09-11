<!-- capsule-v2 -->
# Reverse-sweep incremental recompute — how do you recompute parent groups after a field-id migration?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does the second (post-processing) incremental algorithm rebuild parent groups from changed children, and why does it process values in REVERSE lexicographic order?

## FacetsUpdateIncrementalInner.find_changed_parents
**Path/Symbol:** `crates/milli/src/update/facet/new_incremental.rs:FacetsUpdateIncrementalInner` (`execute` :59-75, `find_changed_parents` :80-213, `compute_parent_group` :215-378) — used by `update/new/indexer/post_processing/mod.rs:19` and fed by `update/new/merger.rs:FacetFieldIdDelta{Bulk | Incremental(Vec<FacetFieldIdChange>)}` (:195-214).
**Signature:** `fn find_changed_parents(&self, wtxn: &mut RwTxn, mut changed_children: Vec<FacetFieldIdChange>) -> Result<()>`; `fn compute_parent_group(&self, wtxn, parent_level: u8, parent_left_bound: Box<[u8]>) -> Result<()>`.
**Data Shape:** Input = changed facet values as raw encoded bytes; `FacetFieldIdDelta::push(facet_value, max_count)` degrades to `Bulk` once the change vector exceeds `max_count` — the SAME bulk-vs-incremental economics as the classic dispatcher, applied per post-processing field.

### Decisive source
```rust
// new_incremental.rs:63-70
self.delta_data.sort_unstable_by(
    |FacetFieldIdChange { facet_value: left, .. },
     FacetFieldIdChange { facet_value: right, .. }| {
        left.cmp(right)
            // sort in **reverse** lexicographic order
            .reverse()
    },
);

// new_incremental.rs:100-105 — the last-parent cache that reverse order enables
if let Some(last_parent) = &last_parent {
    if &child.facet_value >= last_parent {
        self.compute_parent_group(wtxn, child_level, child.facet_value)?;
        continue 'current_level;
    }
}

// new_incremental.rs:279-290 — adaptive group sizing keeps the tree balanced
let group_size = if child_count >= self.max_group_size as usize * 2 {
    self.max_group_size as usize
} else if child_count >= self.group_size as usize {
    child_count / 2          // size in [group_size, max_group_size*2[ ⇒ balanced halves
} else {
    child_count              // take everything
};
```

**Flow:** Sort changed values in REVERSE lexicographic order; then level by level (`child_level 0..u8::MAX`, swapping `changed_children ↔ changed_parents` between levels): for each changed child, either reuse the cached `last_parent` (when child ≥ cached bound) or binary-search the enclosing parent via a rev-range query; when NO parent exists (child is below the level's first key), delete the old first key, adopt the child's value as the new left bound, and drain all remaining children against it. `compute_parent_group` recomputes one parent entry by walking its children with an ADAPTIVE group size (see excerpt), deleting empty groups, until the whole child range under the parent is regrouped. Finally `add_or_delete_level` grows/shrinks the top.
**Invariant:** (1) The reverse sort makes "child ≥ last_parent" the common case so each parent group is computed exactly once per level — forward order would re-walk the same parent repeatedly; (2) `compute_parent_group` on `parent_level == 0` is a no-op guard; (3) neighbor-fid/level spill is checked defensively before adopting a new left bound (:147-150).
**Probe:** `crates/milli/src/update/facet/incremental_test.rs` exercises the classic twin; this variant is pinned indirectly via `update/new` integration suites — direct observable executed this pass: `cargo test -p milli --lib -- facet` GREEN at pin. Coverage caveat: no dedicated unit test names `find_changed_parents`; behavior verified at the `FacetFieldIdDelta::Bulk` degradation seam in merger tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "find_changed_parents compute_parent_group FacetFieldIdChange", limit: 10 });
```

## Verdict
Adopt the reverse-lexicographic sweep + last-parent cache + adaptive group sizing; adapt the delta-vector source to host extraction; omit the v1-indexer (`merger.rs`) context if your host only runs the new indexer path.
