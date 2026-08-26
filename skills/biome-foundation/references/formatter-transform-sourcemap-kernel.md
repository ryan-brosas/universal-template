<!-- capsule-v2 -->
# TransformSourceMap deleted-range algebra — how do you map positions of a tree that had nodes deleted from it back to original source, with O(log n) lookups and no per-token markers?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a pre-processing pass (e.g. parenthesis removal) deletes text — what data structure recovers original positions for verbatim printing and sourcemaps while storing only the DELETED ranges?

## Deleted ranges + accumulated offsets + trimmed-range extension
**Path/Symbol:** `crates/biome_formatter/src/source_map.rs` (828L) — module doc rationale (:1-45); `TransformSourceMap { source_text, deleted_ranges: Vec<DeletedRange>, mapped_node_ranges: FxHashMap<TextSize, TrimmedNodeRangeMapping> }` (:47-55); lookups `source_offset` (:156) / `source_offset_with_range` (:175-221); `resolve_trimmed_range` fixpoint (:97-115); builder `TransformSourceMapBuilder` (:424-535: `with_offset` :444 for non-document-start roots, `add_deleted_range` :465 accepts OUT-OF-ORDER input, `extend_trimmed_node_range` :478 inserts ONE mapping under BOTH endpoints, `finish` :495 sort+merge); `DeletedRange { source_range, total_length_preceding_deleted_ranges }` (:378-422, `transformed_start = source_start − preceding_deleted` :417); public iterator `DeletedRanges`/`DeletedRangeEntry` (:537-600, DoubleEnded).
**Signature:** `pub fn source_range(&self, transformed_range: TextRange) -> TextRange` (O(log n)); `pub fn trimmed_source_text<L: Language>(&self, node: &SyntaxNode<L>) -> &str`.
**Data Shape:** NOT a generic source map: only deletion-supporting transforms qualify ("without changing the order of the tokens" needs NO source map at all). Storage is one sorted Vec of merged deletions + a hash map keyed by node-range START AND END positions.

### Decisive source
```rust
// source_map.rs:185-205 — the Start/End ASYMMETRY at an exact boundary hit:
if range.transformed_start() == transformed_offset {
    match position {
        RangePosition::Start => range.source_end(),
        // `a)`, deleted range is right after the token. That's why `source_start` is the
        // offset that truncates the `)` and `source_end` includes it
        RangePosition::End => range.source_start(),
    }
}
// else: source_start + len + (transformed_offset - transformed_start)
```
```rust
// source_map.rs:507-523 — finish(): adjacent ranges MERGE into one mapping:
self.deleted_ranges.sort_by(|a, b| match a.start().cmp(&b.start()) {
    Ordering::Equal => a.end().cmp(&b.end()), ordering => ordering });
let mut last_mapping = DeletedRange::new(self.deleted_ranges[0], TextSize::default());
let mut transformed_offset = last_mapping.len();
for range in self.deleted_ranges.drain(1..) {
    if last_mapping.source_range.end() == range.start() {
        last_mapping.source_range = last_mapping.source_range.cover(range);
    } else {
        merged_mappings.push(last_mapping);
        last_mapping = DeletedRange::new(range, transformed_offset);
    }
    transformed_offset += range.len();
}
```
```rust
// source_map.rs:97-115 — trimmed ranges resolve by ITERATING to fixpoint:
loop {
    let resolved = self.resolve_trimmed_range(mapped_range);
    if resolved == mapped_range { break resolved; } else { mapped_range = resolved; }
}
```
**Flow:** transform walks tokens pushing every deleted `(start,end)` + original text (`push_source_text`) → `finish()` sorts (ties broken by end), merges ADJACENT deletions, computes each mapping's preceding-deleted-byte total → queries binary-search `transformed_offset` against `transformed_start()` keys; exact hits disambiguate by `RangePosition` (Start wants the range's END in source, End wants its START — this is what keeps `a` inside `(a+b)` from swallowing a paren); verbatim/suppressed printing calls `trimmed_source_text`, which maps then repeatedly extends via `mapped_node_ranges` until stable so `a+b` regains `(a+b)`. `map_markers` (:228-282) re-bases printer markers the same way but handles line-suffix OUT-OF-ORDER markers by re-binary-searching instead of advancing the cursor.
**Invariant:** the debug_assert in `DeletedRange::new` (`source_range.start() >= total_length_preceding_deleted_ranges`) encodes that transformed offsets can never precede their own accumulated deletions; merging adjacent ranges at finish is load-bearing for "only ever a single mapping starting at the same transformed offset". The `(a + b)` example set (`a→a`, `a+b→(a+b)`, whole-stmt → full parens) is the acceptance test for any port.
**Probe:** `grep -n 'fn source_offset_with_range' crates/biome_formatter/src/source_map.rs` → 1 hit :175; `sed -n '193p' …` shows `RangePosition::Start => range.source_end()`; `grep -c 'binary_search_by_key' …` → 2; `grep -n 'last_mapping.source_range.cover(range)' …` → 1 hit :516; direct tests: `range_mapping` :611 (adds ranges OUT OF ORDER :630-631, asserts all five letter positions), `trimmed_range` :678 (`((a))` extension), `deleted_ranges` :759 (iterator entries).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"TransformSourceMapBuilder"}'
# biome.crates.biome_formatter.src.source_map TransformSourceMapBuilder Struct 424-434
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"DeletedRangeEntry"}'
# DeletedRangeEntry Struct 537-546
```

## Verdict
Adopt the deleted-range algebra wholesale for any delete-only CST pre-process (paren stripping, semicolon removal, dialect-node erasure); adapt `extend_trimmed_node_range` call sites to whichever nodes your host prints verbatim on error/suppression; omit `mapped_node_ranges` entirely if you never print transformed nodes verbatim. This capsule executes the pass-10 standing conditional #2. Coverage: no_recorded_issue + generation_matches @ 2026-08-16T00:20:04Z.
