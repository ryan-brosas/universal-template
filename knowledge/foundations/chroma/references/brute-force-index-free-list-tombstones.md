<!-- capsule-v2 -->
# Brute force index free-list tombstones — How does the ephemeral batch index keep positional arrays consistent under delete?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** The BruteForceIndex is a fixed numpy matrix with dict-based indexing — what is the delete/visibility contract a porter must copy?

## BruteForceIndex
**Path/Symbol:** `chromadb/segment/impl/vector/brute_force_index.py:BruteForceIndex` (:17-151).
**Signature:** `upsert(records)`, `delete(records)`, `has_id(id) -> bool`, `query(query) -> Sequence[Sequence[VectorQueryResult]]`; constructed with `size=batch_size, dimensionality, space`.
**Data Shape:** Preallocated `vectors = np.zeros((size, dim))`; `id_to_index`/`index_to_id` dicts; `free_indices` LIFO stack; `deleted_ids` set; NaN-filled rows for deleted slots.

### Decisive source
```python
def delete(self, records):
    ...
        self.deleted_ids.add(id)
        del self.id_to_index[id]
        del self.index_to_id[index]
        del self.id_to_seq_id[id]
        self.vectors[index].fill(np.nan)
        self.free_indices.append(index)

def has_id(self, id: str) -> bool:
    return id in self.id_to_index and id not in self.deleted_ids

# query(): full argsort over ALL rows, then filter:
for j in index_list:
    if j in self.index_to_id:          # never-allocated rows skipped
        id = self.index_to_id[j]
        if id not in self.deleted_ids and (allowed_ids is None or id in allowed_ids):
            curr_results.append(...)
```

**Flow:** upsert pops a free slot or overwrites in place (and revokes pending deletes); delete marks + NaN-fills + returns the slot to the freelist; query sorts every row's distance then filters by allocation/tombstone/allow-list — deliberately simple because n ≤ batch_size (~100). Not thread-safe by contract; callers hold the write lock.
**Invariant:** A slot may be reused only after its ID is fully unlinked from both dicts and seq map; visibility = allocated ∧ not-deleted ∧ allowed. Distance function chosen once by space string (l2/ip/cosine via `chromadb.utils.distance_functions`) so scores are comparable with the HNSW arm during merge.
**Probe:** `/tmp/chroma-p1/probe_battery.py` bfi.nan_fill / bfi.freelist byte-exact greps (GREEN); upstream `chromadb/test/segment/impl/vector/test_brute_force_index.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "BruteForceIndex upsert delete free_indices deleted_ids argsort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt freelist+NaN-tombstone slot management for small bounded vector buffers; adapt distance functions to your metric set; omit the O(n·m) double apply_along_axis scoring — any real port should batch it.
