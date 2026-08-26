<!-- capsule-v2 -->
# Generational NodeCache GC — how does an interner of immutable green trees evict entries without reference-count overhead?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How can a hash-consing cache for syntax nodes/tokens/trivia bound its memory across many parsed files while entries are shared Arc'd subtrees that must not be freed early?

## NodeCache: generation bit + retain sweep
**Path/Symbol:** `crates/biome_rowan/src/green/node_cache.rs:NodeCache` (:166-172), `GenerationalPointer` (:27-92), `node()` (:224-284), `token_with_trivia()` (:290-320), `increment_generation` (:325-342), `retain_cache` (:346-356), `VacantNodeEntry::cache` (:403-420).
**Signature:** `struct GenerationalPointer<T: IntoRawPointer> { data: usize }` — pointer in the high bits, generation enum (A=0/B=1) in bit 0, legal because green allocations are aligned > 1 byte.
**Data Shape:** `nodes/tokens: hashbrown HashMap<Cached*, ()>` driven via `raw_entry_mut().from_hash(hash, eq)` with *manually provided* hashes (`FxHasher`; node hash = kind + children's pre-computed hashes; token hash = kind + text; trivia hash = pieces). `CachedNode { ptr+gen, hash: u64 }` stores its hash because recomputing means walking the subtree.

### Decisive source
```rust
// every hit re-stamps the entry as "touched this file":
RawOccupiedEntry => entry.key_mut().node.set_generation(self.generation);
// flip once per parse, then drop everything not touched:
pub(crate) fn increment_generation(&mut self) {
    debug_assert!(self.nodes.keys().all(|e| e.node.generation() == self.generation)
        && /* tokens, trivia likewise */);
    self.generation = !self.generation;
}
pub(crate) fn retain_cache(&mut self) {
    self.nodes.retain(|node, _| node.node.generation() == self.generation);
    // same for tokens and trivia
}
```

**Flow:** query by manual hash → hit: re-stamp generation, return clone → vacant: insert stamped with current generation → after a tree finishes, `increment_generation()` then `retain_cache()`, so exactly the entries used by the most recent parse survive into the next.
**Invariant:** Two generations suffice because eviction runs between parses while all live entries share one stamp. The debug assertion inside `increment_generation` pins the protocol: you may not flip generations with mixed stamps present (i.e., retain must follow every increment before more inserts... actually inserts during the new generation re-stamp on access — the assert holds only when called at a quiescent point, which is why callers invoke it right after finishing a tree). Kind changes at insert time (`VacantNodeEntry::cache`: queried kind ≠ final bogus/unknown kind ⇒ return `UNCACHED_NODE_HASH = 0`, never insert) prevent unmatchable lookups from poisoning the table.
**Probe:** in-file `crates/biome_rowan/src/green/node_cache.rs` `#[cfg(test)] mod tests` — `cache_entry_size` pins CachedNode=16B/CachedToken=8B/CachedTrivia=8B (the packing contract); `green_token_hash` pins hash-equal trivia normalization.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "NodeCache increment_generation retain_cache generation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-generation touch-stamping for any shared interner needing cheap LFAU-style eviction (macro caches, module registries); adapt hashing to your element identity; omit the ≤3-slot caching cutoff if your nodes are cheaper to build than to hash. Coverage caveat: full-mode index, metadata_match.
