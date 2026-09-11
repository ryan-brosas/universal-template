<!-- capsule-v2 -->
# map_markers out-of-order re-basing — how do you remap a printer's source markers through deleted ranges when line-suffix comments make the marker stream NON-monotonic?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** the fast path advances one cursor over sorted deleted ranges — what exactly must happen when a marker's source position jumps BACKWARD mid-stream?

## Cursor advance + binary-search rewind hybrid
**Path/Symbol:** `crates/biome_formatter/src/source_map.rs` — `TransformSourceMap::map_printed` (:221-226, applies to `printed.sourcemap` in place); `map_markers(&mut [SourceMarker])` (:228-283); out-of-order detection (:239-241 `previous.source > marker.source`); rewind branch (:243-256 binary_search_by_key + index fixup); steady-state advance (:258-270 while-loop); per-marker resolution (:272-281 `source_offset_with_range(marker.source, RangePosition::Start, current_range)`); empty-map early return (:228-231).
**Signature:** `fn map_markers(&self, markers: &mut [SourceMarker])`.
**Data Shape:** input = mutable slice of printer markers (transformed-tree coordinates, possibly out of order). The cursor (`next_range_index`) is a plain Vec index over merged DeletedRanges; on rewind it is recomputed from scratch via binary search.

### Decisive source
```rust
// source_map.rs:239-256 — the rewind arm with its own index arithmetic:
let out_of_order_marker =
    previous_marker.is_some_and(|previous| previous.source > marker.source);

if out_of_order_marker {
    let index = self.deleted_ranges
        .binary_search_by_key(&marker.source, |range| range.transformed_start());
    match index {
        Ok(index) => { next_range_index = index + 1; }   // direct hit: resume AFTER it
        Err(index) => { next_range_index = index; }      // insert point: resume AT it
    }
} else {
    // Find the range for this mapping. In most cases this is a no-op or only involves
    // a single step because markers are most of the time in increasing source order.
    while next_range_index < self.deleted_ranges.len() {
        let next_range = &self.deleted_ranges[next_range_index];
        if next_range.transformed_start() > marker.source { break; }
        next_range_index += 1;
    }
}
```
**Flow:** for each marker: detect backward jump → either binary-search-rewind the cursor or advance it → fetch `deleted_ranges.get(next_range_index - 1)` as the governing range (index 0 ⇒ None ⇒ identity mapping) → resolve `marker.source = source_offset_with_range(...)` → store marker as new `previous_marker`. Resolution always uses `RangePosition::Start` here (the Start/End asymmetry lives in the kernel capsule). `map_printed` mutates `printed.sourcemap` and returns the printed value unchanged otherwise.
**Invariant:** the cursor is ONLY valid while marker sources are non-decreasing; every backward jump must fully re-derive it (Ok→index+1 / Err→index), never "step back one". Empty deleted_ranges short-circuits with zero work — transforms without deletions keep byte-identical maps. This is the mechanism behind Printed's documented unsorted-marker guarantee (formatter-printed-envelope).
**Probe:** `grep -n 'out_of_order_marker' crates/biome_formatter/src/source_map.rs` → :240+:243; `grep -c 'binary_search_by_key' crates/biome_formatter/src/source_map.rs` → 2 (rewind here + single lookup at :161); `sed -n '229p' …` shows the `.is_empty()` early return. Direct tests: `range_mapping` :611 (out-of-order `add_deleted_range` calls prove builder-side tolerance) + `deleted_ranges` :759 (sorted iterator contract the cursor relies on).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"map_markers"}'
# TransformSourceMap.map_markers Method 228-282
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"DeletedRangeEntry"}'
# public entry shape yielded by the sorted iterator
```

## Verdict
Adopt the hybrid cursor for any sorted-range remap over a potentially reordered stream; adapt the binary-search key to your offset representation; omit the rewind arm ONLY if your printer provably emits monotonic markers (line-suffix/deferred comments usually break that assumption). Coverage: source_map.rs no_recorded_issue @ generation 2026-08-16T00:20:04Z.
