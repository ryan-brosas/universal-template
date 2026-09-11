<!-- capsule-v2 -->
# Bulk-vs-incremental dispatcher — when does a facet update rebuild the whole tree?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What threshold decides bulk rebuild vs incremental modify for facet levels, and what does the dispatcher silently skip?

## FacetsUpdate.execute
**Path/Symbol:** `crates/milli/src/update/facet/mod.rs:FacetsUpdate` (`execute` :154-201, `index_facet_search` :204-299, `clear_facet_levels` :302-318).
**Signature:** `pub fn execute(self, wtxn: &mut heed::RwTxn<'_>, new_settings: &InnerIndexSettings) -> Result<()>`.
**Data Shape:** `self.data_size: u64` = size of the delta data; `self.database.len(wtxn)` = current number of keys in the facet DB; decision is pure integer comparison — no sampling.

### Decisive source
```rust
// mod.rs:166-187
if self.data_size >= (self.database.len(wtxn)? / 500) {
    let field_ids = facet_levels_field_ids(new_settings);
    let bulk_update = FacetsUpdateBulk::new(
        self.index, field_ids, self.facet_type, self.delta_data,
        self.group_size, self.min_level_size,
    );
    bulk_update.execute(wtxn)?;
} else {
    let incremental_update = FacetsUpdateIncremental::new(
        self.index, self.facet_type, self.delta_data, self.group_size,
        self.min_level_size, self.max_group_size,
    );
    incremental_update.execute(wtxn)?;
}
```
Module doc (:65-70) states the empirical law behind the constant: "it takes 50x more time to incrementally add N facet values to an existing database than it is to construct a database of N facet values."

**Flow:** Early-return when `data_size == 0`; touch `updated_at`; dispatch by the /500 ratio; afterwards, if facet search is DISABLED (`index.facet_search(wtxn)? == false`) it clears the two facet-search DBs (`facet_id_string_fst`, `facet_id_normalized_string_strings`) and returns WITHOUT touching them; otherwise `index_facet_search` applies the normalized-string delta with a live-existence check: a deleted original string only leaves the normalized key's set if its level-0 `FacetGroupKey{field_id, level:0, left_bound:original}` no longer EXISTS (:232-243); then the per-field FSTs are rebuilt from scratch by streaming the normalized DB and splitting on `field_id` changes (:266-292).
**Invariant:** (1) The 1/500 ratio is the contract — porters who substitute "always incremental" get pathological indexing times on large updates, and "always bulk" destroys small-update latency; (2) del entries against a nonexistent level-0 value must NOT remove the original string from the normalized set (another value still normalizes to it); (3) FST rebuild is full-clear-and-recompute per pass, never patched.
**Probe:** `crates/milli/src/update/settings/settings_update_by_task.rs` exercises this via settings updates; direct unit pin: `crates/milli/src/search/facet/search.rs` tests + `crates/filter-parser` integration via `FacetSearchBuilder` — simplest observable: `cargo test -p milli --lib -- facet_search` GREEN at pin (this pass). Dispatcher itself has no dedicated unit test — coverage caveat: behavior pinned indirectly by the bulk/incremental suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "FacetsUpdate data_size bulk incremental execute", limit: 10 });
```

## Verdict
Adopt the delta-size/500-key ratio and the disabled-facet-search clear path; adapt the InnerIndexSettings coupling; omit the meilisearch task-level settings-diff plumbing above it.
