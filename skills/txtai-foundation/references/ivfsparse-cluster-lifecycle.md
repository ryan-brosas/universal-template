<!-- capsule-v2 -->
# IVFSparse cluster lifecycle — how is a sparse IVF index built, pruned, appended to and tombstoned?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How does a from-scratch sparse IVF index decide its cluster count, rebuild after pruning, grow on append, and treat deletes — without corrupting ids?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/ann/sparse/ivfsparse.py:IVFSparse.index` (:59-99), `.append` (:101-115), `.delete` (:117-119), `.search` (:121-137), `.build/.aggregate/.nlist/.nprobe/.cells/.minpoints`.
**Signature:** `index(embeddings)` / `append(embeddings)` / `delete(ids)` / `search(queries, limit)` over scipy CSR matrices.
**Data Shape:** state = `centroids` (sparse vstack or None=exact), `ids {cluster: [rowid]}`, `blocks {cluster: sparse matrix}`, `deletes [rowid]`, `config["offset"]`.

### Decisive source
```python
# Prune small clusters (less than minpoints parameter) and rebuild
indices = sorted(k for k, v in ids.items() if len(v) >= self.minpoints())
if len(indices) > 0 and len(ids) > 1 and len(indices) != len(ids.keys()):
    self.centroids = self.centroids[indices]
    ids = self.aggregate(embeddings)

# Sort clusters by id
self.ids = dict(sorted(ids.items(), key=lambda x: x[0]))

# Create cluster data blocks
self.blocks = {k: embeddings[v] for k, v in self.ids.items()}

# Calculate block max summary vectors and use as centroids
self.centroids = vstack([csr_matrix(x.max(axis=0)) for x in self.blocks.values()]) if self.centroids is not None else None
```

**Flow (index):** derive clusters `max(min(4√count, count/39), 1)` unless nlist setting; ≤5000 rows ⇒ 1 cluster = exact search (no centroids) → MiniBatchKMeans(n_init=5, seed 0) → snap each centroid to the nearest ACTUAL data point → dedupe centroids → aggregate by L2-closest centroid → prune clusters under minpoints(39) AND RE-AGGREGATE everything against pruned centroids → FINAL centroids are per-block column-max summary vectors (not kmeans output!) → blocks built in sorted-cluster-id order.

**Flow (append):** new rows offset by `size()` (total INCLUDING deletes); assigned to existing clusters via `aggregate`; block ids extended with `x + offset`; `config["offset"] += new`.

**Flow (delete):** tombstone only — `self.deletes.extend(ids)`; `count() = size() - len(deletes)`; tombstoned rows zeroed inside `topn` (`scores[:, deletes] = 0`) at scan time. No compaction ever.

**Invariant:** append must NEVER renumber existing row ids — offsets make appends id-stable while blocks stay dense arrays; search threads per query (`queries.shape[0] // 32`, capped by cpu_count) because scipy ops drop the GIL (:124-137). `topn` must re-sort after `argpartition` (:276-278) — argpartition does NOT order within top-n.

**Probe:** `test/python/testann/testsparse.py:testIVFSparse` (:45-91 — index+append+save/load roundtrip, delete decrements count, cluster pruning ≤ nlist), `:testIVFSparseSortOrder` (:93-109 pins the descending-score ordering), `:testIVFSparseTopnOverLimit` (:111-132 limit > doc count).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "IVFSparse aggregate centroids prune nprobe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the build→prune→re-aggregate ladder + max-summary final centroids + offset-stable appends + tombstone deletes; adapt cell-count formula constants (39/4√n) to your density; omit k-means entirely below 5000 rows (exact scan). Probes executed live upstream.
