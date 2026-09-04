<!-- capsule-v2 -->
# es-vectorless-rerank — how does ES rerank without shipping chunk vectors?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** Where do clean cosine scores come from on the ES path now that chunk vectors are no longer fetched in the main search?

## Second-pass KNN-only scoring
**Path/Symbol:** `Dealer._knn_scores` `rag/nlp/search.py:394-425` + `Dealer.rerank_with_knn` `:465-490`; comment contract `:211-218`.
**Signature:** `_knn_scores(sres, idx_names, kb_ids) -> dict[str, float]`; `rerank_with_knn(sres, query, knn_scores, tkweight=0.3, vtweight=0.7, cfield="content_ltks", rank_feature=None)`.
**Data Shape:** second call uses empty `_source` list, filter condition `{"id": list(sres.ids)}`, ONE MatchDenseExpr with `{"similarity": 0.0}`, offset 0 / limit len(ids).

### Decisive source
```python
"""
Second-pass ES call that returns the cosine similarity between the
query embedding and each candidate chunk's embedding, filtered to the
chunk ids the original search already surfaced. We rely on ES to do
the vector math so the chunk vectors never leave the engine.
"""
...
matchDense = MatchDenseExpr(f"q_{dim}_vec", sres.query_vector, "float", "cosine", len(sres.ids), {"similarity": 0.0})
condition = {"id": list(sres.ids)}
res = await thread_pool_exec(self.dataStore.search, [], [], condition, [matchDense], OrderByExpr(), 0, len(sres.ids), ...)
return self.dataStore.get_scores(res)
```

**Flow:** retrieval() dispatch (`:685-698`) → ES branch calls `_knn_scores` then merges: `vtsim[i] = knn_scores.get(chunk_id, 0.0)` (missing id scores ZERO, never errors), `sim = tkweight*tksim + vtweight*vtsim + rank_fea`. Only OceanBase/SerenedB still pull `q_<dim>_vec` into `_source` for local `rerank()`; Infinity/GaussDB use server-side `_score` directly.
**Invariant:** the KNN call must keep `similarity: 0.0` — any inherited threshold silently drops candidates from the score map and rerank zeroes them. Chunk vectors stay in the index; citations fetch them on demand via `fetch_chunk_vectors` (`:427-463`, tab-split string vectors coerced through `get_float`, wrong-dim/absent → zero placeholder).
**Probe:** `grep -n 'def _knn_scores\|def rerank_with_knn\|def fetch_chunk_vectors' rag/nlp/search.py` → exactly :394/:465/:427; `sed -n '211,216p' rag/nlp/search.py | grep -c 'second KNN-only call'` → 1. All executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "_knn_scores cosine similarity chunk ids second pass", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt the engine-does-vector-math pattern (ids-filtered threshold-free KNN probe); adapt merge weights via config as upstream does; omit the legacy local `rerank()` vector transport unless porting the OceanBase backend.
