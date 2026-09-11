<!-- capsule-v2 -->
# Level navigation helpers — how do you find the tree height and first/last value in O(1)?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** What exact key prefixes do the three facet-tree navigation helpers use, and why does every consumer need them?

## get_highest_level / get_first_facet_value / get_last_facet_value
**Path/Symbol:** `crates/milli/src/search/facet/mod.rs` (`get_first_facet_value` :62-83, `get_last_facet_value` :86-107, `get_highest_level` :110-126, `facet_min_value` :79-89 area).
**Signature:** `pub(crate) fn get_highest_level<'t, DC>(txn, db, field_id: u16) -> heed::Result<u8>`; `get_first_facet_value<'t, BoundCodec, DC>(txn, db, field_id) -> heed::Result<Option<BoundCodec::DItem>>`.
**Data Shape:** All keys share the LMDB layout `[field_id: u16 BE][level: u8][left_bound bytes]` — so a 2-byte field prefix ranges over ALL levels of one field, and a 3-byte `[fid][0]` prefix isolates level 0.

### Decisive source
```rust
// mod.rs:110-126 — the whole trick: last key of the field IS the highest level
Ok(db.remap_types::<Bytes, DecodeIgnore>()
    .rev_prefix_iter(txn, field_id_prefix)?   // prefix = field_id.to_be_bytes()
    .next()
    .map(|el| { let (key, _) = el.unwrap();
        let key = FacetGroupKeyCodec::<BytesRefCodec>::bytes_decode(key).unwrap();
        key.level })
    .unwrap_or(0))

// mod.rs:73-77 — first value = first LEVEL-0 key (3-byte prefix)
let mut level0prefix = vec![];
level0prefix.extend_from_slice(&field_id.to_be_bytes());
level0prefix.push(0);
```

**Flow:** `get_highest_level` reverse-iterates everything under the field-id prefix and decodes the level byte of the first hit (empty ⇒ 0); first/last facet values iterate level-0 only (prefix `[fid][0]`) forward/backward and decode the left bound. Consumers: every search algorithm starts at `(highest_level, first_bound)`; descending sort additionally needs `last_bound`; min/max facet values run the sort iterators and take the first yielded bitmap.
**Invariant:** (1) Level numbering is dense from 0 — there is no level gap (bulk rebuild and both incremental algorithms maintain this; #3165 was a gap), which is what makes "last key = top level" valid; (2) helpers return DECODED bound types via the caller's codec, not raw bytes.
**Probe:** exercised by every facet test module (`facet_range_search_test.rs`, sort/distribution suites all call these on entry); direct observable executed this pass: `cargo test -p milli --lib -- facet` GREEN at pin. Coverage caveat: no standalone unit tests — behavior is pinned transitively by every consumer suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "get_highest_level get_first_facet_value get_last_facet_value rev_prefix_iter", limit: 10 });
```

## Verdict
Adopt the key-layout arithmetic (2-byte field scan for height, 3-byte level-0 scan for extremes); adapt codec generics to host encoding; omit nothing — it's ~60 lines of pure contract.
