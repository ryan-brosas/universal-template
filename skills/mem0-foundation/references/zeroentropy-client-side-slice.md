<!-- capsule-v2 -->
# ZeroEntropy rerank client-side truncation — full list first, slice after sort

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** when the rerank API has no `top_n` parameter, where must the top-k cut happen?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/zero_entropy_reranker.py`: `ZeroEntropyReranker.rerank` (:72-92); default model at :44 (`self.model = config.model or "zerank-1"`).
**Signature:** `rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]`.
**Data Shape:** API returns scored results for ALL sent documents; client maps them back via `result.index`, then sorts and slices locally.

### Decisive source
```python
response = self.client.models.rerank(
    model=self.model,
    query=query,
    documents=doc_texts,
)
...
reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)

# Apply top_k limit
if top_k:
    reranked_docs = reranked_docs[:top_k]
elif self.config.top_k:
    reranked_docs = reranked_docs[:self.config.top_k]
```

**Flow:** send every doc text → map results onto copies by index → explicit descending sort on `rerank_score` (the API response order is NOT trusted) → only THEN apply `top_k` (argument beats config) → no third fallback: with neither set, the FULL ranked list is returned.
**Invariant:** sorting precedes slicing — a port that slices before sorting returns an arbitrary subset of documents; a port that trusts response order skips the sort. Note the deliberate contrast with the Cohere sibling (`cohere-server-side-topn`): same contract shape, opposite cut location; do not unify them blindly.
**Probe:** `grep -cF "reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)" mem0/reranker/zero_entropy_reranker.py` (=1); `grep -cF 'reranked_docs = reranked_docs[:self.config.top_k]' mem0/reranker/zero_entropy_reranker.py` (=1).
**Probe (direct test):** `tests/rerankers/test_reranker_fallback_topk.py` mirrors the same three tests for the ZeroEntropy arm (:41/:50/:59); `tests/rerankers/test_reranker_fallback_no_mutation.py::TestZeroEntropyFallbackNoMutation` (:33) pins copy-on-stamp; happy-path sort/slice itself remains SDK-contract level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "models.rerank zerank relevance_score", limit: 10 });
```

## Verdict
Adopt fetch-all → index-remap → sort-descending → slice as the canonical client-side-truncation shape for top_n-less APIs; adapt model default (`zerank-1`) to your provider's naming; omit server-side `top_n` plumbing that this backend does not support.
