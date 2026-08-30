<!-- capsule-v2 -->
# DB cache — pointer cache with universe-intersecting decode

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does the search hot path avoid re-decoding LMDB bitmaps, and how is a per-call universe filter applied WITHOUT materializing the full bitmap twice?

## DatabaseCache: Cow pointers + intersection_with_serialized
**Path/Symbol:** `crates/milli/src/search/new/db_cache.rs:DatabaseCache` (:26-48), `get_value` (:50-84), `get_value_from_keys` (:114-169), `word_docids` exact∪tolerant merge (:183-205), `get_db_word_prefix_pair_proximity_docids` ByAttribute/ByWord split (:451-520), `get_db_word_fids` (:575-599).
**Signature:** `fn get_value<'v, K1, KC>(txn, cache_key: K1, db_key: &KC::EItem, cache: &mut FxHashMap<K1, Option<Cow<'ctx,[u8]>>>, universe: Option<&RoaringBitmap>, db: Database<KC, Bytes>) -> Result<Option<RoaringBitmap>>`
**Data Shape:** 15 per-database maps keyed by interned words (+proximity/fid/position tuples); values are `Option<Cow<Borrowed bytes>>` — a POINTER into the LMDB map, never an owned decode on the cache-hit path.

### Decisive source
```rust
match (bitmap_bytes, universe) {
    (bytes, Some(universe)) =>
        CboRoaringBitmapCodec::intersection_with_serialized(bytes, universe).map(Some)...,
    (bytes, None) =>
        CboRoaringBitmapCodec::bytes_decode_owned(bytes).map(Some)...,
}
// get_value_from_keys: restricted-fid lookups merge N per-field bitmaps:
[keys] => db.get(txn, key)?.map(Cow::Borrowed),
keys => { ... Some(merger.merge(&[], &bitmaps[..])?) }
```

**Flow:** Miss ⇒ `db.get` stores borrowed bytes in the map; hit ⇒ skip LMDB entirely (FxHashMap lookup only). Decode happens per CALL: either full CboRoaringBitmapCodec decode or — when a universe is supplied — a streamed intersection against the serialized CBOR-compressed bitmap without allocating the full set. attributesToSearchOn routes word lookups through word_fid_docids (one key per restricted fid) merged with MergeCboRoaringBitmaps.
**Invariant:** (1) The cache stores BYTES not decoded bitmaps so one entry serves both filtered and unfiltered callers; negative results (`None`) are cached too. (2) Proximity precision ByAttribute collapses proximity to key 0 ("same attribute") and computes docids as per-field intersections of word∈fid bitmaps — the DB never stores word pairs across fields; ByWord prefix-scans `(proximity, w1, w2*)`. (3) Prefix enumeration helpers (get_db_word_fids) append `\0` to the word to form the StrBEU16 prefix and back-fill the per-pair caches while scanning.
**Probe:** No single upstream unit test pins DatabaseCache directly (it is exercised by every search test, e.g. typo.rs suite GREEN at HEAD) — coverage caveat recorded honestly; the capsule's contract is pinned by source inspection of :50-84/:114-169 at pin 577f7af2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "DatabaseCache", limit: 5 });
```

## Verdict
Adopt pointer-caching + serialized-intersection pattern for any LSM/LMDB-backed posting-list engine; adapt codec to host's bitmap format; omit heed type remapping specifics. Caveat: no dedicated direct test file; behavior verified via the passing search suites.
