<!-- capsule-v2 -->
# Facet level-tree bulk rebuild — how do you rebuild the facet docid levels from scratch without losing values?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** When a large share of the facet database changes, how is the multi-level `facet_id_(string/f64)_docids` tree rebuilt from scratch, and what does a porter get wrong about the leftover-group flush rule?

## FacetsUpdateBulkInner.update / compute_higher_levels
**Path/Symbol:** `crates/milli/src/update/facet/bulk.rs:FacetsUpdateBulkInner` (`update` :98-113, `update_level0` :115-187, `read_level_0` :198-244, `compute_higher_levels` :252-351).
**Signature:** `fn update(mut self, wtxn: &mut RwTxn<'_>, field_ids: &[u16]) -> Result<()>`; `fn compute_higher_levels(&self, rtxn, field_id, level: u8, handle_group: &mut dyn FnMut(&[RoaringBitmap], &'t [u8]) -> Result<()>) -> Result<Vec<grenad::Reader<BufReader<File>>>>`.
**Data Shape:** LMDB DB keyed `FacetGroupKey{field_id:u16, level:u8, left_bound:bytes}` valued `FacetGroupValue{size:u8, bitmap:CboRoaringBitmap}`; `delta_data` is an Option<grenad Merger> of DelAdd bitmaps (None ⇒ level 0 untouched); constants `FACET_GROUP_SIZE=4`, `FACET_MIN_LEVEL_SIZE=5`.

### Decisive source
```rust
// bulk.rs:319-349 — the leftover flush rule that produced #3165
if !bitmaps.is_empty() && (cur_writer_len >= self.min_level_size as usize - 1) {
    // the length of bitmaps is between 0 and group_size
    assert!(bitmaps.len() < self.group_size as usize);
    ...
}
// if we inserted enough elements to reach the minimum level size, then we push the writer
if cur_writer_len >= self.min_level_size as usize {
    sub_writers.push(writer_into_reader(cur_writer)?);
} else {
    // otherwise ... we give them to the level above
    if !bitmaps.is_empty() { handle_group(&bitmaps, left_bounds.first().unwrap())?; }
}

// bulk.rs:179-183 — empty result of del+add deletes the whole level-0 key
let new_bitmap = &buffer[1..];
// if the new bitmap is empty, let's remove it
if CboRoaringBitmapLenCodec::bytes_decode(new_bitmap).unwrap_or_default() == 0 {
    database.delete(wtxn, key)?;
} else {
    database.put(wtxn, key, &buffer)?;
}
```

**Flow:** `update` = (1) apply delta to level 0 via `update_level0` (merge del-add into existing bitmap; delete key when the merged bitmap becomes empty; on an EMPTY db, silently ignore all Del entries and APPEND additions), (2) `clear_facet_levels` deletes every key with level ≥ 1 for the touched fields, (3) for each field, `compute_higher_levels(…, 32, …)` recursively rebuilds levels bottom-up: each callback group of `group_size` bitmaps is OR-folded into one parent entry whose `size = sub_bitmaps.len()`; a partially-filled final level is written out only when `cur_writer_len >= min_level_size - 1`, else its leftovers are handed to the level above so no docids are lost.
**Invariant:** (1) Every level ≥1 entry's `size` equals its number of children in the level below — search algorithms (`get_highest_level`, range/sort walkers) trust it; (2) a level is only materialized when it reaches `min_level_size` entries; undersized leftovers must propagate UP (never dropped) or higher-level searches miss documents (#3165 was exactly this: a lossy `as u8` comparison skipped a level); (3) level-0 keys with empty bitmaps are deleted, not stored.
**Probe:** `crates/milli/src/update/facet/bulk.rs` tests `insert` (:367-398) + `bug_3165` (:448-488) — parameterized group/min-level shapes plus the regression pinning 22,541 facet values produce ALL levels. GREEN at pin (`cargo test -p milli --lib -- facet`, this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "FacetsUpdateBulkInner update_level0 compute_higher_levels", limit: 10 });
```

## Verdict
Adopt the bottom-up group-OR fold, the min_level_size materialization threshold with upward leftover propagation, and empty-bitmap key deletion; adapt the grenad temp-writer spooling to host storage; omit the milli `Index`/settings plumbing (`facet_levels_field_ids`) around it.
