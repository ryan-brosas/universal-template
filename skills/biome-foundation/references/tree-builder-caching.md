<!-- capsule-v2 -->
# Green-node builder caching — when does finish_node reuse a cached subtree instead of rebuilding it?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the tree builder hash-cons nodes whose children were produced by a SyntaxFactory that may change kinds?

## TreeBuilder::finish_node three-way cache
**Path/Symbol:** `crates/biome_rowan/src/tree_builder.rs:TreeBuilder` (:25-215), cache entry enum in `crates/biome_rowan/src/green/node_cache.rs`; `CowMut<'a, T>` (`crates/biome_rowan/src/cow_mut.rs`, 30L) makes `with_cache(&mut NodeCache)` borrow or own transparently.
**Signature:** `pub fn with_cache(cache: &mut NodeCache) -> TreeBuilder<'_, L, S>`; `fn finish_node(&mut self)`; `Checkpoint(NonZeroUsize)` for `start_node_at`.
**Data Shape:** `parents: Vec<(Kind, usize /* first_child idx */)>`, `children: Vec<(u64 /*hash*/, GreenElement)>`. Cache lookup happens on `(raw_kind, slots)` BEFORE the factory runs.

### Decisive source
```rust
let slots = &self.children[first_child..];
let node_entry = self.cache.node(raw_kind, slots);   // lookup FIRST (pre-factory kind)
let mut build_node = || {
    let children = ParsedChildren::new(&mut self.children, first_child);
    S::make_syntax(kind, children).into_green()      // factory may change kind / fill holes
};
let (hash, node) = match node_entry {
    NodeCacheNodeEntryMut::NoCache(hash) => (hash, build_node()),          // uncacheable (kind changed)
    NodeCacheNodeEntryMut::Vacant(entry) => { let node = build_node(); let hash = entry.cache(node.clone()); (hash, node) }
    NodeCacheNodeEntryMut::Cached(cached) => {
        self.children.truncate(first_child);                               // drop built children!
        (cached.hash(), cached.node().to_owned())
    }
};
```

**Flow:** `start_node(kind)` records the child-index watermark → tokens/nodes accumulate → `finish_node`: cache-lookup by kind+slots → hit: truncate children and reuse the cached green node (structurally shared); miss: run the factory, insert into cache → `finish()` asserts exactly one root child remains, then `retain_cache()` applies generation-bit GC.
**Invariant:** A node whose kind was *changed* by `make_syntax` can never be cached (the lookup already happened with the old kind) — hence the three-way enum. Nodes with differing empty-slot patterns are distinct cache entries even at the same kind (pinned by the two in-file tests). The doc contract requires `make_syntax` to be idempotent: same kind + same children ⇒ structurally identical output.
**Probe:** `crates/biome_rowan/src/tree_builder.rs::tests::caches_identical_nodes_with_empty_slots` + `doesnt_cache_node_if_empty_slots_differ` (direct #[test]s asserting pointer-identical vs distinct elements).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TreeBuilder finish_node node cache", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `tree_builder.TreeBuilder.finish_node` (:114-143).

## Verdict
Adopt the pre-factory cache probe + three-way outcome whenever your green builder runs a normalizing factory; adapt slot hashing; omit CowMut in favor of your host's borrow/own idiom. Direct tests exist in-file — cite them rather than inventing corpus probes.
