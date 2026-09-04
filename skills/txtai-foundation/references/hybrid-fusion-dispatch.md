<!-- capsule-v2 -->
# Hybrid fusion strategy dispatch — which math fuses dense+sparse results for a given sparse scoring config?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** When both a dense ANN and a sparse scoring index are enabled, how must results be fused, and what determines the fusion algorithm?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/search/hybrid.py:Hybrid.__init__` (:18-31), `Hybrid.__call__` (:33-46); dispatch site `src/python/txtai/embeddings/search/base.py:Search.search` (:107-119).
**Signature:** `Hybrid(scoring)` → sets `self.method`; `__call__(self, vectors, weights, limit)` where `vectors = (dense_results, sparse_results)`, `weights = [dense_weight, sparse_weight]`.
**Data Shape:** dense/sparse results are lists of `(uid, score)` sorted desc; weights arrive as a single number from `Search.search` and are split `[w, 1 - w]`.

### Decisive source
```python
hybrid = self.ann and self.scoring
dense = self.dense(queries, limit * 10 if hybrid else limit) if self.ann else None
sparse = self.sparse(queries, limit * 10 if hybrid else limit) if self.scoring else None

if hybrid:
    # Create weights array if single number passed
    if isinstance(weights, (int, float)):
        weights = [weights, 1 - weights]

    # Create weighted scores via hybrid fusion strategy
    fusion = Hybrid(self.scoring)
    return [fusion(vectors, weights, limit) for vectors in zip(dense, sparse)]
```

**Flow:** candidate over-fetch (`limit * 10` per side, only when hybrid) → weight split `[w, 1-w]` → per-query fusion method selected ONCE at construction:
- `scoring.isbayes()` → `LogOdds` (log-odds conjunction)
- `scoring.isnormalized()` → `convex` (weighted sum of scores)
- else → `rrf` (weighted reciprocal-rank)

**Invariant:** The three methods consume DIFFERENT score semantics — convex needs normalized scores, rrf consumes only ranks (`score` discarded), LogOdds needs BB25 probabilities. Porting the wrong one silently corrupts ranking; selection is driven by the sparse index's normalization flags (`Scoring.isbayes/isnormalized`), not by user-facing config strings.

### LogOdds detail (Bayesian path, :108-248)
Per query: collect `(raw_dense, p_sparse)` pairs; calibrate dense with `beta = median(raw>0)`, `alpha_eff = 1/std`; fuse only docs present in BOTH lists as `l̄ = w0·clip(α(d−median)) + w1·logit(p_sparse)`, scaled by `√n` (n=2, scale=√2); single-signal docs keep their own calibrated logit × their weight; final map through sigmoid `1/(1+e^-x)` back to [0,1]. Numerical clamp ±500 / EPSILON=1e-10.

**Probe:** `test/python/testembeddings.py:testHybrid` (:206-253 — hybrid True, then `normalize=False` forcing RRF, then `"bb25"` forcing LogOdds all return uid 4/uid 1 as top hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Hybrid convex rrf logodds fusion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way dispatch keyed on `isbayes/isnormalized` + the `limit * 10` candidate over-fetch + `[w, 1-w]` weight split; adapt the LogOdds calibration constants to your scorer's score distribution; omit the specific BB25 paper citation wiring if you have no Bayesian normalizer (RRF is the safe default). Coverage caveat: no dedicated unit suite isolates `Hybrid`; behavior is pinned end-to-end via `testHybrid`.
