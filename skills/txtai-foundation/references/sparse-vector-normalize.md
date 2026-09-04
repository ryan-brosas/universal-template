<!-- capsule-v2 -->
# Sparse vector scoring + normalization dispatch — how do neural-sparse scores become fusable [0,1] numbers?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How does a sparse-vector (learned-term-weight) index encode, search, and normalize its scores so hybrid fusion stays correct?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/scoring/sparse.py:Sparse.insert/.index/.upsert` (:55-97), `.batchsearch` (:106-114), `.start/.stop/.encode/.stream` (:145-202), `.normalize` (:204-239); normalizer `scoring/normalize.py:Normalize.bayes` (:81-120).
**Signature:** `batchsearch(queries, limit)` → normalized `[(uid, score)]`; `normalize: True|float|"bb25"|"bayes"|False`.
**Data Shape:** documents stream through a bounded `Queue(5)` into an encoder thread; results land in a sparse ANN (`SparseANNFactory` → ivfsparse/pgsparse); `config["dimensions"]` stamped by the encoder.

### Decisive source
```python
def batchsearch(self, queries, limit=3, threads=True):
    # Convert queries to embedding vectors
    embeddings = self.model.batchtransform((None, query, None) for query in queries)

    # Run ANN search
    scores = self.ann.search(embeddings, limit)

    # Normalize scores if normalization IS enabled AND vector normalization IS NOT enabled
    return self.normalize(embeddings, scores) if self.isnormalize and not self.model.isnormalize else scores
```
```python
# linear path: scale default 30.0; maxscore floor guards against tiny self-similarity
scale = 30.0 if isinstance(self.isnormalize, bool) else self.isnormalize
maxscores = self.model.dot(queries, queries)
maxscore = max(maxscores[x][x] / scale, scale)
maxscore = max(maxscore, result[0][1]) if result else maxscore
results.append([(uid, score / maxscore) for uid, score in result])
```

**Flow:** insert batches → queue → background thread encodes via `model.vectors(...)` streaming generator (`COMPLETE=1` EOS sentinel) → `index()`/`upsert()` drains the thread (`stop()` joins + returns embeddings) and builds/appends the sparse ANN. Query: batchtransform queries → ANN search → normalize unless the model already emits normalized vectors (`model.isnormalize`).

**Invariant:** The double-negative guard (`isnormalize AND NOT model.isnormalize`) prevents double normalization — a porter applying both linear scaling AND a model that self-normalizes silently flattens rankings. Bayesian mode (`"bb25"/"bayes"` aliases) swaps linear max-scaling for per-query sigmoid calibration: positive-score candidates only, `beta=median`, `alpha=abs(α/std)`, zero-score candidates STAY 0.0 (candidate-set behavior), logits clipped ±500. This probability output is exactly what flips Hybrid into LogOdds fusion — the two contracts interlock.

**Probe:** `test/python/testscoring/testkeyword.py:normalize` (:356-398 — ranking preserved under bayes, all scores in [0,1], bb25 alias equivalence, zero stays zero); `test/python/testembeddings.py:testHybrid` bb25 branch (:243-253).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Sparse batchsearch normalize bayes queue encode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the encode-thread + EOS-drain pipeline and the double-normalization guard; adapt scale 30.0 to your score distribution; omit bayes if your fusion never consumes probabilities. Coverage caveat: probes live in testkeyword/testembeddings integration suites.
