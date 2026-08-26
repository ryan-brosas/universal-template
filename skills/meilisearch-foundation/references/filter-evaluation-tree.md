<!-- capsule-v2 -->
# Filter evaluation tree — how does a parsed filter become a RoaringBitmap, and what does AND pass down?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What universe does each boolean branch receive, and which operator fast paths bypass the level tree entirely?

## IndexFilter.inner_evaluate / evaluate_operator
**Path/Symbol:** `crates/milli/src/search/facet/filter/index_filter.rs:IndexFilter` (`evaluate` :59-89, `evaluate_operator` :91-268, `explore_facet_levels` :314-346, `inner_evaluate` :348-747) + `crates/milli/src/search/facet/filter/value_bounds.rs` (`ValueBounds::new` :21-87, `evaluate_equal` :93-119).
**Signature:** `fn inner_evaluate(&self, rtxn, index, field_ids_map, rules: &[FilterableAttributesRule], universe_hint: Option<&RoaringBitmap>) -> Result<RoaringBitmap>`.
**Data Shape:** `universe_hint` = candidate restriction handed DOWN the recursion (None ⇒ whole index); `ValueBounds` classifies every operator into Range/Equal/NotEqual/Contains/StartsWith/FieldIsNull/Empty/Exists with BOTH normalized-string and parsed-number forms.

### Decisive source
```rust
// index_filter.rs:446-476 — AND threads the running bitmap as the child universe
let mut bitmap = Self::inner_evaluate(&first..., rtxn, ..., universe_hint)?;
for f in subfilters_iter {
    if bitmap.is_empty() { return Ok(bitmap); }        // early-out
    bitmap &= Self::inner_evaluate(&(f.clone()).into(), rtxn, ..., Some(&bitmap))?;
}

// value_bounds.rs:215-238 (index_filter.rs) — STARTS WITH becomes a byte range
// The idea here is that "STARTS WITH baba" is the same as "baba <= value < babb".
let mut value2 = normalized.as_bytes().to_owned();
match value2.last_mut() {
    None => return index.exists_faceted_documents_ids(rtxn, field_id)..., // empty prefix ⇒ EXISTS
    Some(last) if *last == u8::MAX => return Ok(RoaringBitmap::new()),     // cannot increment
    Some(last) => *last += 1,
}
find_docids_of_facet_within_bounds::<BytesRef>(rtxn, bytes_db, field_id,
    &Included(normalized.as_bytes()), &Excluded(value2.as_slice()), universe_hint, &mut docids)?;
```

**Flow:** Pre-validate EVERY fid against filterable-attribute rules once (:66-86), then recurse: `Not` = universe − inner; `Or` = union (MultiOps); `In` = union of Equal per element; `And` = fold with the running bitmap as next child's universe hint + early-exit on empty; unknown field ids short-circuit to EMPTY bitmap (not error — error happened in pre-validation). Operators: comparisons build dual number/string bounds and call `explore_facet_levels` (which first rejects inverted ranges: `Included(l)>Included(r)` etc. ⇒ empty); equality = two O(1) level-0 point lookups UNIONED (`evaluate_equal`); NotEqual = all-docs − equal; Contains = memmem scan over level-0 string keys with LazyDecode; StartsWith = increment-last-byte range trick above. Geo branches combine rtree radius walk and cellulite polygon shapes.
**Invariant:** (1) The AND-universe threading is what makes range search's lazy intersection correct AND cheap — dropping it forces full-decode unions; (2) inverted ranges MUST yield empty before hitting the tree (the level walker assumes left ≤ right); (3) empty STARTS WITH prefix degrades to EXISTS (all docs having the field).
**Probe:** `crates/milli/src/search/facet/filter/tests.rs` — `empty_db` (:53), `from_array` (:76), `not_filterable` (:136), `filter_depth` (:458, 14,361-term OR parses), `filter_number` (:536). GREEN at pin (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "IndexFilter inner_evaluate evaluate_operator explore_facet_levels universe_hint", limit: 10 });
```

## Verdict
Adopt the universe-threading AND fold, operator→ValueBounds classification, and the starts-with/inverted-range/contains fast paths; adapt roaring/MultiOps to host bitmap lib; omit shard filters (`_shard` internal field) and cellulite geojson twins unless porting those features.
