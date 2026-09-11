<!-- capsule-v2 -->
# Interner trio + SmallBitmap — the search plane's memory discipline

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** Why does every graph structure use u16 handles instead of pointers/strings, and what allocation/lifetime contract does a porter break by using HashMap<String,_> everywhere?

## Interned<T> / DedupInterner / FixedSizeInterner / MappedInterner
**Path/Symbol:** `crates/milli/src/search/new/interner.rs` (whole file, 259L): `Interned<T>` (:12-27), `DedupInterner<T>` (:33-77), `FixedSizeInterner<T>` (:84-135), `Interner<T>` (:141-186), `MappedInterner<From,T>` (:196-220); consumer `small_bitmap.rs:SmallBitmap`.
**Signature:** `pub struct Interned<T> { idx: u16, _phantom }` — Copy + Eq/Ord/Hash by idx alone.
**Data Shape:** Words, phrases, query terms, conditions, edges, even graph NODES live in interners; `SmallBitmap<T>` is a bitset over an interner's universe (`for_interned_values_in(&interner)`), so predecessor/successor sets are 1-2 words per node.

### Decisive source
```rust
pub fn insert(&mut self, s: T) -> Interned<T> {
    if let Some(interned) = self.lookup.get(&s) { *interned }
    else {
        assert!(self.stable_store.len() < u16::MAX as usize);   // hard capacity law
        self.stable_store.push(s.clone());
        let interned = Interned::from_raw(self.stable_store.len() as u16 - 1);
        ...
    }
}
// freeze(): DedupInterner -->> FixedSizeInterner — mutation phase ends,
// lookups become pure indexing with no hash map at all.
```

**Flow:** Build phase uses DedupInterner (dedup + lookup map) or growable Interner; `freeze()` converts to FixedSizeInterner (Vec only) before traversal; MappedInterner projects one interner onto another index space (e.g. per-node cost tables `nodes.map(|_| vec![])`). Comparing/hashing two conditions is a u16 compare; cloning a whole RankingRuleGraph clones four Vec-backed interners.
**Invariant:** (1) **u16 ceiling**: any interner holds < 65,536 values — enforced by assert, and MAX_TOKEN_COUNT=1_000 on parsed tokens keeps this reachable; a porter raising limits must widen Interned's index type everywhere simultaneously. (2) Interned<T> equality is INDEX equality: two structurally equal Conditions inserted into DIFFERENT interners are not interchangeable — condition dedup only works within one interner instance. (3) Sets-of-things are SmallBitmaps over the interner, so "remove node" = clear bit + mark Deleted; iteration order = insertion order (deterministic bucketing).
**Probe:** No dedicated upstream unit test pins interner.rs in isolation (covered transitively by all search suites GREEN at HEAD); contract pinned by direct source inspection at pin 577f7af2 — caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "DedupInterner", limit: 5 });
```

## Verdict
Adopt handle-based interning + freeze + bitset-sets as the memory architecture for any graph search kernel; adapt element types freely; omit fxhash choice. Caveat: no isolated direct test — behavior verified through passing suites.
