<!-- capsule-v2 -->
# Faiss component-string derivation — how is an IVF index auto-sized when the user gives no components?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must a Faiss wrapper derive index components, cell counts, nprobe, and id mapping when config omits them?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/ann/dense/faiss.py:Faiss.configure` (:124-157), `.cells` (:184-197), `.components` (:199-218), `.nprobe` (:220-232), `.index/.append` (:56-90), `.scores` (:234-252).
**Signature:** `configure(count, train)` → components string for `faiss.index_factory(dim, params, METRIC_INNER_PRODUCT)`.
**Data Shape:** settings under `config["faiss"]`; root-level `quantize` bool|int; `config["offset"]` = next rowid.

### Decisive source
```python
# Derive quantization. Prefer backend-specific setting. Fallback to root-level parameter.
quantize = self.setting("quantize", self.config.get("quantize"))
quantize = 8 if isinstance(quantize, bool) else quantize

# Get storage setting
storage = f"SQ{quantize}" if quantize else "Flat"

# Small index, use storage directly with IDMap
if count <= 5000:
    return "BFlat" if self.qbits else f"IDMap,{storage}"

x = self.cells(train)
components = f"BIVF{x}" if self.qbits else f"IVF{x},{storage}"
```
```python
# cells: x = min(4 * sqrt(embeddings count), embeddings count / 39); Faiss requires >=39 points per cluster
return max(min(round(4 * math.sqrt(count)), int(count / 39)), 1)

# nprobe default: 6 if count <= 5000 else cells(count) // 16
```

**Flow:** index → optional `sample` fraction for the training matrix (`np.random.default_rng(0)`, sorted indices, replace=False shuffle=False — deterministic) → configure components → `index_factory(..., METRIC_INNER_PRODUCT)` (inner product == cosine because vectors are L2-normalized upstream) → `train(train)` → `add_with_ids(embeddings, arange(n))` → stamp `offset` + build metadata. Append continues ids from `offset`. Binary path (qbits): `index_binary_factory` + `IndexBinaryIDMap` wrap for BFlat/BHNSW + hamming score `clip(1 - dist/(dims*8))`.

**Invariant:** IDs are POSITIONAL (`arange`) and delete uses `remove_ids`, so any external id mapping lives in Embeddings.ids/database — never inside Faiss. The ≤5000 flat-vs-IVF switch and the 39-points-per-cell floor are load-bearing: ignoring them yields untrained/empty-cell warnings and garbage recall. `nprobe` derived at SEARCH time each call (:96-101), not frozen at build.

**Probe:** `test/python/testann/testdense.py:testFaiss` (:66-72 shared runTests matrix), `testFaissBinary` (:73-87 BHash32 search >0), `testFaissCustom` (:88-97 PCA16,IDMap,SQ8 + bare IVF,SQ8 components strings exercising `.components` cell-fill), `testFaissMmap` (:120-127).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Faiss configure cells nprobe components quantize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the derivation ladder (components override → quantize storage → 5k flat/IVF split → cells formula → nprobe=cells//16); adapt thresholds; omit binary/BHash paths unless you need 1-bit indexes. Coverage caveat: probes run through the shared ANN test matrix; macOS OMP env workarounds (:9-15) are host-specific.
