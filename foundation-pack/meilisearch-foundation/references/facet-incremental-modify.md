<!-- capsule-v2 -->
# Incremental level modify FSM — how do you add/remove ONE facet value without rebuilding the tree?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What is the full result alphabet of an in-place level-0..N modify, and when does each outcome propagate, split, or shrink a node?

## FacetsUpdateIncrementalInner.modify_in_level
**Path/Symbol:** `crates/milli/src/update/facet/incremental.rs:FacetsUpdateIncrementalInner` (`modify` :524-555, `modify_in_level` :384-515, `modify_in_level_0` :216-272, `split_group` :278-342, `find_insertion_key_value` :170-210, `add_or_delete_level` :561-577) — `enum ModificationResult` :48-55.
**Signature:** `pub fn modify(&self, txn, field_id, facet_value: &[u8], add_docids: Option<&RoaringBitmap>, del_docids: Option<&RoaringBitmap>) -> Result<bool>`; recursive `fn modify_in_level(&self, txn, field_id, level: u8, facet_value, add, del) -> Result<ModificationResult>`.
**Data Shape:** Six-state result: `InPlace | Expand | Insert | Reduce{next} | Remove{next} | Nothing`. `modify` returns bool = "a node was added or removed at the highest level ⇒ caller must run `add_or_delete_level`".

### Decisive source
```rust
// incremental.rs:471-514 — the split trigger and the trim-before-delete guard
if updated_value.size < self.max_group_size {
    // If there are docids to delete, trim them avoiding unexpected removal.
    if let Some(del_docids) = del_docids
        .map(|ids| self.trim_del_docids(txn, field_id, level, &insertion_key,
                                        insertion_value_size, ids))
        .transpose()?.filter(|ids| !ids.is_empty())
    { updated_value.bitmap -= &*del_docids; ... }
    ...
    self.db.put(txn, &insertion_key.as_ref(), &updated_value)?;
    Ok(insertion_key_modification)
} else {
    // We've increased the group size of the value and realised it has become
    // greater than or equal to `max_group_size`. Therefore it must be split.
    self.split_group(txn, field_id, level, insertion_key, updated_value)
}

// incremental.rs:443-457 — left-bound maintenance on the insertion path
if let ModificationResult::Remove { next } | ModificationResult::Reduce { next } = result {
    let reduced_range = facet_value == insertion_key.left_bound;
    if reduced_range {
        new_insertion_key.left_bound = next.clone().unwrap();
        key_modification = ModificationResult::Reduce { next };
    }
} else if facet_value < insertion_key.left_bound.as_slice() {
    new_insertion_key.left_bound = facet_value.to_vec();
    key_modification = ModificationResult::Expand;
}
```

**Flow:** For each delta entry (sorted by field): `modify` walks from `highest_level` DOWN to 0 recursively; level 0 does the real bitmap math (`(bitmap - del) | add`, full key deletion when empty with `next` = following same-field/same-level left bound); every higher level re-finds its insertion key via `get_lower_than_or_equal_to` (falling back to the level's FIRST key when the hit is a different level), adjusts `size` (+1 on child Insert, −1 on child Remove, delete-self when size would hit 0), maintains its left bound via Expand/Reduce, applies `trim_del_docids` so a docid present in SEVERAL children is not removed from a group where it still lives, and splits into two balanced halves (`size_left = size/2`) when size reaches `max_group_size`. Only `Insert|Remove` bubbling out of the top ⇒ true ⇒ deferred `add_or_delete_level` (grow a level when `size_highest >= group_size * min_level_size`, delete it when `< min_level_size && highest != 0`).
**Invariant:** (1) Node sizes vary in [1, max_group_size] after incremental updates (unlike bulk's fixed group_size) — search code must never assume uniform groups; (2) `trim_del_docids` is mandatory before subtracting deletes at any level > 0 — skipping it corrupts bitmaps for multi-valued documents; (3) `Nothing` short-circuits the recursion — no writes above the lowest changed level; (4) `add_or_delete_level` runs once per FIELD after all its entries, not per entry.
**Probe:** `crates/milli/src/update/facet/incremental_test.rs` — `prepend`/`append`/`shuffled` (:11-123), `delete_from_end/start/shuffled` (:146-286), `in_place_level0_insert/delete` (:286-339) pin all six outcomes. GREEN at pin (executed this pass via `cargo test -p milli --lib -- facet`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "FacetsUpdateIncrementalInner modify_in_level split_group ModificationResult", limit: 10 });
```

## Verdict
Adopt the six-state result alphabet, trim-before-delete, and the deferred per-field level grow/shrink; adapt LMDB put/delete ordering to host KV; omit the grenad delta-merger input format.
