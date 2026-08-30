<!-- capsule-v2 -->
# MMR vector search — when does lambda≥1 mean plain similarity, and how do partitioned searches interleave?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How is Maximal Marginal Relevance implemented over an in-memory numpy store, what disables it, and how do per-partition searches merge?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/llms.py:VectorStore.max_marginal_relevance_search` (:111-170), `NumpyVectorStore.similarity_search/partitioned_similarity_search` (:207-274), `QdrantVectorStore.add/similarity/load_docs` (:367-442).
**Signature:** `async def max_marginal_relevance_search(self, query, k, fetch_k, embedding_model, partitioning_fn=None) -> tuple[Sequence[Embeddable], list[float]]`.
**Data Shape:** `texts_hashes: set[int]` membership via `__contains__` (hash-of-object) drives lazy index building (`docs._build_texts_index` adds only `t not in self.texts_index`). Query embedding runs under `EmbeddingModes.QUERY` then resets to DOCUMENT.

### Decisive source
```python
if len(texts) <= k or self.mmr_lambda >= 1.0:
    return texts, scores                      # MMR DISABLED: default lambda=1.0
similarity_matrix = cosine_similarity(embeddings, embeddings)
selected_indices = [0]                        # top-similarity seeds MMR
while len(selected_indices) < k:
    max_sim_to_selected = similarity_matrix[:, selected_indices].max(axis=1)
    mmr_scores = self.mmr_lambda * np_scores - (1 - self.mmr_lambda) * max_sim_to_selected
    mmr_scores[selected_indices] = -np.inf
    selected_indices.append(mmr_scores.argmax())
# partitioned: per-partition k results interleaved round-robin:
[t for t in itertools.chain.from_iterable(itertools.zip_longest(*texts)) if t is not None][:k]
```

**Flow:** similarity_search (or partitioned) fetches `fetch_k=2*k` → if λ<1 rerank by MMR seeded at rank-0 → slice k. Partitioning (clinical trials use `partition_clinical_trials_by_source`) guarantees each source group contributes before merging round-robin. Qdrant twin: deterministic point ids `uuid5(NAMESPACE_URL, str(embedding))` make upserts idempotent; payloads exclude embedding; `load_docs` scrolls batches under a semaphore and rebuilds Docs.
**Invariant:** `fetch_k >= k` enforced; nan similarities map to -inf so zero-vector texts can't dominate; `_texts_filter` is instance state mutated during partitioned search — reset in finally-position (:226) and documented CPU-bound serial loop.
**Probe:** `tests/test_paperqa.py::test_context_comparison` (:3768) + retrieval paths of `test_json_evidence` (:875); executed grep pins mmr_lambda>=1.0 short-circuit :144 and uuid5 id derivation llms.py:387.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "max_marginal_relevance_search NumpyVectorStore cosine_similarity partitioned", limit: 10 });
```

## Verdict
Adopt the vectorized MMR + λ≥1 disable switch + round-robin partition interleave; adapt stores (swap Qdrant for pgvector keeping the interface); omit the Qdrant loader if you persist Docs separately. Coverage caveat: numeric behavior pinned by cited tests, not a fresh run.
