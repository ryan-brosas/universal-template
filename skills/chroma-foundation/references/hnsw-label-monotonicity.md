<!-- capsule-v2 -->
# HNSW label monotonicity — How do integer labels stay stable across adds, updates, and deletes without renumbering?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** A porter must know how external string IDs map to hnswlib's internal integer labels and what happens to labels on update/delete/resize.

## LocalHnswSegment._apply_batch / _write_records
**Path/Symbol:** `chromadb/segment/impl/vector/local_hnsw.py:_apply_batch` (:243-288), `_write_records` (:290-328).
**Signature:** `_apply_batch(self, batch: Batch) -> None`; labels allocated as `next_label = self._total_elements_added + 1`, incremented only for IDs **not already present**.
**Data Shape:** `_id_to_label: Dict[str,int]`, `_label_to_id: Dict[int,str]`, `_id_to_seq_id: Dict[str,SeqId]` (kept for compatibility; comment says no longer needed). Labels start at 1 (total starts 0).

### Decisive source
```python
next_label = self._total_elements_added + 1
for i in range(len(written_ids)):
    if written_ids[i] not in self._id_to_label:
        labels_to_write[i] = next_label
        next_label += 1
    else:
        labels_to_write[i] = self._id_to_label[written_ids[i]]

index = cast(hnswlib.Index, self._index)

# First, update the index
index.add_items(vectors_to_write, labels_to_write)

# If that succeeds, update the mappings
for i, id in enumerate(written_ids):
    self._id_to_seq_id[id] = batch.get_record(id)["log_offset"]
    self._id_to_label[id] = labels_to_write[i]
    self._label_to_id[labels_to_write[i]] = id

# If that succeeds, update the total count
self._total_elements_added += batch.add_count
```

**Flow:** delete phase first (`mark_deleted(label)` + dict removals, skipping unknown IDs) → ensure index capacity → allocate labels → `add_items` (existing label = in-place vector update) → mirror into dicts → bump counter. Deletes never free or reuse a label: `_total_elements_added` counts *additions*, not live rows, so labels grow monotonically forever and `knn_query` filter closures stay valid across mutations.
**Invariant:** A label, once assigned to an ID, is never reassigned to a different ID; the ID↔label maps are mutated only AFTER the hnswlib call succeeds (crash between steps leaves index ahead of maps, not behind).
**Probe:** `grep -c 'next_label = self\._total_elements_added + 1' chromadb/segment/impl/vector/local_hnsw.py` → 1; direct tests `chromadb/test/segment/impl/vector/test_local_hnsw.py` (upstream suite; requires hnswlib).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_apply_batch next_label mark_deleted add_items", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the monotonic-label + apply-order contract for any hnswlib-style port (it is what makes label-set filtering safe); adapt capacity growth (DEFAULT_CAPACITY=1000, resize_factor 1.2 via `_ensure_index`); omit the vestigial `_id_to_seq_id` map if your storage tracks seq ids elsewhere.
