<!-- capsule-v2 -->
# Multi-index delete choreography — one id list fanned to ann, scoring, subindexes and graph

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must a delete propagate across every index type while keeping content rows, positional ids and tombstones consistent?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/base.py:Embeddings.delete` (:203-258); id resolution helper `embeddings/search/ids.py:Ids.__call__` (:31-49).
**Signature:** `delete(ids)` → list of deleted uids (sorted, deduped).
**Data Shape:** external uid → internal `(indexid, uid)` pairs via database.ids() or in-memory scan; deletes return the UID set, not indexids.

### Decisive source
```python
if self.database:
    # Retrieve indexid-id mappings from database
    ids = self.database.ids(ids)

    # Parse out indices and ids to delete
    indices = [i for i, _ in ids]
    deletes = sorted(set(uid for _, uid in ids))

    # Delete ids from database
    self.database.delete(deletes)
elif self.ann or self.scoring:
    # Find existing ids
    for uid in ids:
        indices.extend([index for index, value in enumerate(self.ids) if uid == value])

    # Clear embeddings ids
    for index in indices:
        deletes.append(self.ids[index])
        self.ids[index] = None

# Delete indices for all indexes and data stores
if indices:
    if self.isdense():
        self.ann.delete(indices)          # positional indexids
    if self.issparse():
        self.scoring.delete(indices)      # positional indexids
    if self.indexes:
        self.indexes.delete(indices)
    if self.graph:
        self.graph.delete(indices)
```

**Flow:** translate external uids → indexids ONCE (database-backed or linear scan of the no-content ids array) → delete content rows → fan positional indexids to every enabled store → return deduped sorted uids. No-content mode tombstones `self.ids[index] = None` (positional holes preserved).

**Invariant:** The fan-out uses INDEXIDS (positions), while the return value uses UIDS — conflating them corrupts every store. Unknown uids are silently ignored (no exception): Terms.delete skips ids not in `self.ids` (`... if i in self.ids`, terms.py:123-133) and TFIDF.documents pops with default — both were crash sites fixed upstream (testDeleteUnknownId). Count semantics differ per backend: ann.count() post-delete (faiss remove_ids), NumPy non-zero rows, scoring len(ids)-len(deletes).

**Probe:** `test/python/testembeddings.py:testDelete` (:110-126), `testscoring/testkeyword.py:testDeleteUnknownId` (:150-166), `testann/testsparse.py:testIVFSparse` delete branch (:76-78).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "delete ids database ann scoring graph indices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt resolve-once/fan-positionals/return-uids + silent unknown-id handling; adapt per-backend tombstone mechanics; omit subindex/graph legs when absent.
