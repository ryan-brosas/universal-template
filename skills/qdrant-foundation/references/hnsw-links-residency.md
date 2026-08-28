<!-- capsule-v2 -->
# HNSW memory residency ladder — how do graph links choose between cold mmap, page-cache, and pinned RAM?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** How does `HnswConfig.memory` (and the deprecated `on_disk` flag) map to link residency at open time, and what does each level guarantee?

## Cold / Cached / Pinned residency selection
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw.rs`: `HNSWIndex::open` memory mapping (:103-119), `links_heap_size_bytes` doc (:138-145), `populate`/`clear_cache` (:157-176); enum `GraphLinksResidency::{Cold, Cached, Pinned}` in `graph_links.rs`.
**Signature:** `let memory = hnsw_config.memory_placement().clamp_to_low_memory(); let is_on_disk = memory.is_on_disk();` then `GraphLayers::load(path, residency, LINK_COMPRESSION_CONVERT_EXISTING)`.
**Data Shape:** config: `Memory::{Cold, Cached, Pinned}` (fallback path from deprecated `on_disk` bool); runtime knobs: node-wide low-memory mode clamps the request; build-time always on-disk (`is_on_disk = true`, "Always skip loading graph to RAM on build").

### Decisive source
```rust
// Effective placement of the graph links: the `memory` parameter (falling back to the
// deprecated `on_disk` flag), degraded at load time by the node-wide low-memory mode.
let memory = hnsw_config.memory_placement().clamp_to_low_memory();
let residency = match memory {
    Memory::Cold   => GraphLinksResidency::Cold,    // Keep the links cold: lazily loaded, cached with usage
    Memory::Cached => GraphLinksResidency::Cached,  // Pre-populate the links into the page cache on load
    Memory::Pinned => GraphLinksResidency::Pinned,  // Materialize the links on heap, never evicted
};
```
Heap-vs-mmap accounting:
```rust
/// Heap RAM held by the graph links, in bytes.
///
/// Non-zero when the links are materialized in RAM rather than backed by
/// a live mmap handle (freshly built index, or a non-borrowable universal-IO
/// backend); such links are invisible to page-cache residency probes.
pub fn links_heap_size_bytes(&self) -> usize
```

**Flow:** open → resolve placement (config → deprecation fallback → low-memory clamp) → pick residency → `GraphLayers::load` with optional inline-vector compression format → `populate()` warms the disk cache on demand; `clear_cache()` drops it; freshly built indexes hold heap-backed links until reopened through the mmap path.
**Invariant:** (1) BUILD always writes on-disk format regardless of target residency — residency is an OPEN-time decision; (2) low-memory mode can only DOWNGRADE (Pinned→Cached→Cold direction), never upgrade; (3) heap-held links are invisible to page-cache probes — memory reporting must consult `links_heap_size_bytes` separately or undercounts Pinned segments; (4) `LINK_COMPRESSION_CONVERT_EXISTING = false`: existing graphs are never silently rewritten at open.

**Probe:** `grep -c "GraphLinksResidency\|clamp_to_low_memory" lib/segment/src/index/hnsw_index/hnsw.rs` → prints `5`. Coverage caveat: no unit test pins the clamp order; behavior documented in-source and here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "GraphLinksResidency GraphLayers load links_heap_size_bytes memory_placement clamp_to_low_memory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-level residency vocabulary and open-time-only placement. Adapt eviction mechanics to host mmap stack. Omit inline-storage compression internals (`StorageGraphLinksVectors`).
