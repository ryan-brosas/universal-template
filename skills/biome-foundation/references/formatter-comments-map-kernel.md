<!-- capsule-v2 -->
# CommentsMap flat-parts kernel — how are per-node leading/dangling/trailing comment lists stored with one allocation for >99.99% of trees?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a naive three-multimap-per-node comment store costs up to `3 × nodes` allocations — what data structure gets one shared Vec while still answering leading/dangling/trailing slices?

## The storage seam
**Path/Symbol:** `crates/biome_formatter/src/comments/map.rs` — `CommentsMap { index, parts, out_of_order }` (:44-58), push trio (:70-176), cold demotion `entry_to_out_of_order` (:179-208), `InOrderEntry` index algebra (:464-588), `PartIndex(NonZeroU32)` (:612-640).
**Signature:** `push_leading/push_dangling/push_trailing(&mut self, key: K, part: V)`; lookups return `&[V]`: `leading()/dangling()/trailing()`.
**Data Shape:** `index: FxHashMap<K, Entry>` where Entry = InOrder{leading_start, dangling_start, trailing_start: Option, trailing_end: Option} | OutOfOrder{leading_index}; ALL parts live in ONE `Vec<V>` (`parts`); `out_of_order: Vec<Vec<V>>` in multiples of 3 (L/D/T). `PartIndex` stores value+1 so `Option<PartIndex>` is pointer-sized; max parts = u32::MAX−1 (documented safe: every comment ≥2 bytes).

### Decisive source
```rust
// map.rs:86-91 — the fast path: appending to the SAME part-class is legal
// while this key's run is still the tail of the shared Vec:
Some(Entry::InOrder(entry))
    if entry.trailing_start.is_none() && self.parts.len() == entry.range().end =>
{
    self.parts.push(part);
    entry.increment_leading_range();   // just moves the L/D boundary
}
// increment_leading_range asserts trailing_start.is_none() — extending a
// leading run after dangling started would corrupt the slice algebra.
```
**Flow:** pushes append into `parts` and widen boundaries while the entry's range ends exactly at `parts.len()` AND no later class has started (L before D before T). First out-of-order push (e.g. trailing then leading) #[cold]-demotes the entry: copies its current ranges into three dedicated Vecs under `out_of_order`, flips the enum. Lookups read either a slice of `parts` or one of the three Vecs; `parts(key)` iterates L→D→T through a 3-state `PartsIterator` that re-binds itself as each segment drains.
**Invariant:** insertion order per key MUST be leading→dangling→trailing for the flat path — measured at >99.99% of real comments because the builder walks source order (:29-38 doc). The increment methods' asserts are load-bearing: they encode which boundary transitions are legal. Porters who allow arbitrary interleaving on the flat path will silently produce overlapping slices; porters who drop NonZeroU32 pay an extra byte per stored index.
**Probe:** map.rs test mod — `leading_dangling_trailing` :649-669 (flat path, exact `map.parts == [1,2,3,4]`), `dangling_leading` :761-779 (out-of-order: parts order [2,1,3,4], correct per-class views), `trailing_leading` :782-800, `keys_out_of_order` :820-840.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "CommentsMap push_leading push_dangling", limit: 10, fields: ["signature", "name", "file"] });
// CommentsMap.push_leading / .push_dangling map.rs 70-141 (line-exact)
```

## Verdict
Adopt the flat-Vec + boundary-index design anywhere you store ordered sub-sequences per key with mostly-monotone insertion (comments, annotations, trivia); adapt V/Clone bounds; omit the out-of-order fallback only if your producer provably inserts in canonical order (then assert it). Coverage caveat: none material — the unit suite covers both paths including all three out-of-order permutations.
