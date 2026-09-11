<!-- capsule-v2 -->
# Cohere reranker server-side top_n — why does the API call get a default of "all documents"?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how is `top_k` resolved for a rerank API that truncates SERVER-side, and what does the caller receive when neither caller nor config supplies it?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/cohere_reranker.py`: `CohereReranker.rerank` API call (:69-76) and result mapping (:79-84).
**Signature:** `rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]`.
**Data Shape:** sends extracted doc texts; receives `response.results` of `{index, relevance_score}` pointing back into `documents`.

### Decisive source
```python
response = self.client.rerank(
    model=self.model,
    query=query,
    documents=doc_texts,
    top_n=top_k or self.config.top_k or len(documents),
    return_documents=self.config.return_documents,
    max_chunks_per_doc=self.config.max_chunks_per_doc,
)
...
for result in response.results:
    original_doc = documents[result.index].copy()
    original_doc['rerank_score'] = result.relevance_score
```

**Flow:** `top_k` precedence = argument → config → `len(documents)` (server returns everything, reordered by relevance) → results are mapped back through `result.index` onto COPIES of the original dicts with `rerank_score` stamped.
**Invariant:** there is NO post-hoc slice and NO re-sort — ordering comes from the API response itself, and `len(documents)` as the final fallback means the method always returns ALL docs ranked rather than a subset. A port that passes `top_n=None` relies on provider defaults (may silently truncate), and one that slices client-side to `top_k` AFTER requesting fewer than all docs loses nothing only because the server already truncated — keep the three-rung ladder intact. `return_documents` stays config-owned: the code never reads returned document bodies, it rebuilds from its own list via `index`.
**Probe:** `grep -cF 'top_n=top_k or self.config.top_k or len(documents)' mem0/reranker/cohere_reranker.py` (=1); `grep -cF 'return_documents=self.config.return_documents' mem0/reranker/cohere_reranker.py` (=1).
**Probe (direct test):** `tests/rerankers/test_reranker_fallback_topk.py` pins the Cohere arm — `test_fallback_respects_config_top_k` (:12), `test_fallback_per_call_top_k_overrides_config` (:21), `test_fallback_returns_all_when_no_top_k` (:30, the `len(documents)` rung); `tests/rerankers/test_reranker_fallback_no_mutation.py::TestCohereFallbackNoMutation` (:20) pins copy-on-stamp.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "client.rerank top_n relevance_score index", limit: 10 });
```

## Verdict
Adopt the three-rung `top_n` ladder + index-based result remapping onto copies; adapt model/config fields (`max_chunks_per_doc`, `return_documents`) to your provider's surface; omit any client-side resorting — the API order IS the output order.
