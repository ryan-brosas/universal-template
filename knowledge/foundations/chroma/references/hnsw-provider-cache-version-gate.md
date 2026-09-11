<!-- capsule-v2 -->
# HNSW provider cache version gate — How is a shared ANN index cached without serving a stale version to a query?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Multiple index versions can exist per collection (compaction creates new ids) — what does a cache hit have to prove before it may be returned?

## HnswIndexProvider
**Path/Symbol:** `rust/index/src/hnsw_provider.rs:HnswIndexProvider::get/open/fork/create` (:145-419), `FILES` const (:29-34), `flush_from_memory` (:427-479).
**Signature:** `get(&self, index_id: &IndexUuid, cache_key: &CollectionUuid) -> Option<HnswIndexRef>`; writes serialized through `write_mutex: AysncPartitionedMutex<IndexUuid>` with configured parallelism.
**Data Shape:** Cache key = collection UUID; validity requires the cached inner index's own id to EQUAL the requested IndexUuid; hnswlib persistence = exactly 4 files (`header.bin`, `data_level0.bin`, `length.bin`, `link_lists.bin`).

### Decisive source
```rust
pub async fn get(&self, index_id: &IndexUuid, cache_key: &CacheKey) -> Option<HnswIndexRef> {
    match self.cache.get(cache_key).await.ok().flatten() {
        Some(index) => {
            let index_with_lock = index.inner.read();
            if index_with_lock.hnsw_index.id == *index_id {
                Some(index.clone())      // Arc clone: cheap handle share
            } else {
                None                     // STALE VERSION — must not be served
            }
        }
        None => None,
    }
}
// open()/fork(): double-checked locking around the long fetch:
let hnsw_data = self.fetch_hnsw_segment(id, prefix_path).await?;
match self.get(id, cache_key).await {          // "Double check after long fetch"
    Some(index) => Ok(index),
    None => { /* load on blocking pool then insert */ }
}
```

**Flow:** get → identity check → on miss fetch 4 files in parallel (`fetch_batch` with P0 priority) → double-check → decode buffers into hnswlib data on `spawn_blocking` (CPU-bound load must not stall tokio) → insert. Flush serializes from memory and uploads all four files via `try_join_all`; create() takes the partitioned write mutex BEFORE init because filesystem ops are not atomic.
**Invariant:** A cached entry keyed by collection may represent an OLDER index id than requested (in-flight query after compaction) — serving it would silently answer against pre-compaction state. The docstring records the known LRU-eviction wrinkle and defers to future versioning.
**Probe:** `/tmp/chroma-p1/probe_battery.py` hp.* anchors incl 2× spawn_blocking and try_join_all (GREEN); direct tests under `rust/index/` provider suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "HnswIndexProvider open fork double checked locking spawn_blocking flush", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the identity-gated cache + double-checked async loading pattern for any versioned artifact server; adapt file layout/serialization to your engine; omit S3/CMEK specifics.
