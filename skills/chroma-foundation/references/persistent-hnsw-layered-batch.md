<!-- capsule-v2 -->
# Persistent HNSW layered batch — How do you serve queries for records not yet in the persisted ANN index?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Writes buffer for `hnsw:batch_size` records before touching hnswlib — how does query correctness survive that window, and how must k be adjusted?

## PersistentLocalHnswSegment.query_vectors
**Path/Symbol:** `chromadb/segment/impl/vector/local_persistent_hnsw.py:query_vectors` (:424-517), `_write_records` (:301-366), `count` (:367-373).
**Signature:** `query_vectors(self, query: VectorQuery) -> Sequence[Sequence[VectorQueryResult]]`; over-fetch computed as `hnsw_k = k + self._curr_batch.update_count + self._curr_batch.delete_count`, clamped to `len(self._id_to_label)`.
**Data Shape:** Two layers share one ID space: persisted HNSW (`_id_to_label`) + ephemeral `BruteForceIndex` holding exactly `_batch_size` records; `_curr_batch` tracks pending deletes/updates; `_sync_threshold` controls `persist_dirty()` frequency.

### Decisive source
```python
# Overquery by updated and deleted elements layered on the index because they may
# hide the real nearest neighbors in the hnsw index
hnsw_k = k + self._curr_batch.update_count + self._curr_batch.delete_count
...
with ReadRWLock(self._lock):
    bf_results = self._brute_force_index.query(query)
    hnsw_results = super().query_vectors(hnsw_query)
    ...
    # Filter deleted results that haven't yet been removed from the persisted index
    curr_hnsw_result = [x for x in curr_hnsw_result if not self._curr_batch.is_deleted(x["id"])]
    ...
    while len(curr_results) < min(k, total_results):
        if bf_dist <= hnsw_dist:
            curr_results.append(curr_bf_result[bf_pointer]); bf_pointer += 1
        else:
            id = curr_hnsw_result[hnsw_pointer]["id"]
            # Only add the hnsw result if it is not in the brute force index
            if not self._brute_force_index.has_id(id):
                curr_results.append(curr_hnsw_result[hnsw_pointer])
            hnsw_pointer += 1
```

**Flow:** both arms queried under read lock → pending-deleted IDs filtered from the HNSW arm → two-pointer merge by distance preferring BF on ties → dedupe keeps the FIRST occurrence (BF arm, which holds the newer vector) → after `_batch_size` records `_apply_batch` flushes to HNSW and `clear()`s the BF layer.
**Invariant:** A record present in the BF layer always shadows its stale HNSW twin (updated vectors must win); count() = `len(_id_to_label) + _curr_batch.add_count - _curr_batch.delete_count` so k-clamping sees the logical size. The init ladder loads with `max_elements=max(count*resize_factor, DEFAULT_CAPACITY)` and `is_persistent_index=True`; max_seq_id migrates from pickle legacy field into SQLite `max_seq_id` table via INSERT OR REPLACE at persist time.
**Probe:** `/tmp/chroma-p1/probe_battery.py` lph.* checks (live-executed GREEN): `grep -c 'hnsw_k = k + self\._curr_batch\.update_count + self\._curr_batch\.delete_count' chromadb/segment/impl/vector/local_persistent_hnsw.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "PersistentLocalHnswSegment query_vectors brute force hnsw_k merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layered-index pattern (buffer + shadowing dedupe + over-query compensation) for any ANN index with deferred batch insertion; adapt batch/sync thresholds (`hnsw:batch_size`=100, `hnsw:sync_threshold`=1000 defaults); omit the pickle metadata sidecar in favor of your own durable mapping store — upstream itself flags it with a TODO.
