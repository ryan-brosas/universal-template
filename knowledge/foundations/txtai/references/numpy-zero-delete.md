<!-- capsule-v2 -->
# NumPy zero-fill delete semantics — why deletes blank rows instead of shrinking the array

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must a flat-array vector index implement delete without invalidating positional ids, and how does count stay truthful?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/ann/dense/numpy.py:NumPy.delete` (:62-67), `.search` (:69-86), `.count` (:88-90), `.hammingscore` (:177-204), `.load` legacy fallback (:33-44).
**Signature:** `delete(ids)`; `search(queries, limit)` → `[[(id, score)]]`.
**Data Shape:** backend = 2D array (float32 or uint8 packed bits when qbits); rows indexed positionally; safetensors optional via `setting("safetensors")`.

### Decisive source
```python
def delete(self, ids):
    # Filter any index greater than size of array
    ids = [x for x in ids if x < self.backend.shape[0]]

    # Clear specified ids
    self.backend[ids] = self.tensor(self.zeros((len(ids), self.backend.shape[1])))

def count(self):
    # Get count of non-zero rows (ignores deleted rows)
    return self.backend[~self.all(self.backend == 0, axis=1)].shape[0]
```

**Flow:** delete zeroes rows (never resizes — positional ids of surviving rows stay stable, mirroring Embeddings.delete's `self.ids[index] = None`) → search computes dot products (cosine on normalized vectors) or hamming scores for qbits (`1 - popcount(xor)/(dims*8)` via a 256-entry bit-count lookup table) → argsort desc and zip ids/scores. Out-of-range delete ids are silently dropped.

**Invariant:** Zero-row IS the tombstone: `count()` counts non-zero rows and deleted rows naturally score 0 (filtered later by `score > 0` in Search.dense). A porter that np.delete()s rows renumbers every subsequent id and corrupts the offset contract shared with append (`config["offset"] += n`). The load() ValueError fallback reads pre-7 pickled arrays for backwards compatibility.

**Probe:** `test/python/testann/testdense.py:testNumPy/testNumPyLegacy/testNumPySafetensors` (:233-287 — including legacy pickle load path and safetensors roundtrip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "NumPy delete zeros hammingscore safetensors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt zero-fill tombstones + non-zero-row counting + out-of-range id filtering; adapt hamming table if not doing binary; omit safetensors if your format is npy-only.
