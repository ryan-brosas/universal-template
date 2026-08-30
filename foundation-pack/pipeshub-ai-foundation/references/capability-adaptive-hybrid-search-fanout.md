<!-- capsule-v2 -->
|# Capability-adaptive hybrid search fan-out — how do you run N queries against vector stores that disagree on dense/sparse/text support without forking the search path per provider?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** When one retrieval service must serve Qdrant (client-side sparse vectors), OpenSearch and Redis (server-side BM25), where does the per-provider divergence live so the caller never branches?

## One request builder gated by capabilities negotiated once at construction
**Path/Symbol:** `backend/python/app/modules/retrieval/retrieval_service.py:RetrievalService._execute_parallel_searches` (L798–864 direct HEAD read); capability source `self._capabilities = vector_db_service.get_capabilities()` captured in `__init__` L100.
**Signature:** `_execute_parallel_searches(queries: list[str], filter, limit) -> list[dict]` (score/citationType/metadata/content dicts via `_format_results`).
**Data Shape:** `HybridSearchRequest(dense_query, sparse_query|None, text_query|None, filter, limit, fusion_method=FusionMethod.RRF)` — a plain dataclass sent to `vector_db_service.query_nearest_points(collection_name, requests)` which returns list-of-lists (one batch per query).

### Decisive source
```python
supports_sparse = self._capabilities.supports_sparse_vectors   # Qdrant: True
supports_text   = self._capabilities.supports_server_side_text_search
if sparse_embedder is not None and supports_sparse:
    # parallelise dense AND sparse embedding generation
    (dense_query_embeddings, sparse_query_embeddings) = await asyncio.gather(
        asyncio.gather(*dense_tasks), asyncio.gather(*sparse_tasks))
else:
    dense_query_embeddings = await asyncio.gather(*dense_tasks)
    sparse_query_embeddings = [None] * len(queries)
requests = [HybridSearchRequest(
        dense_query=d,
        sparse_query=s if supports_sparse else None,  # only stores client-side sparse
        text_query=q if supports_text else None,      # only does server-side BM25
        filter=filter, limit=limit,
        fusion_method=FusionMethod.RRF)               # declared PER REQUEST
        for q, d, s in zip(queries, dense_query_embeddings, sparse_query_embeddings)]
```
(L815–843; dedup tail L850–862: `seen_points` set over `point.id`, first-wins, stamps `metadata["point_id"]`.)

**Flow:** caller (`search_with_filters`) → dense embeddings resolved (raise `ValueError("No dense embeddings found")` when absent) → sparse embedder resolved but possibly unused → both legs embedded concurrently → one HybridSearchRequest per query → store-side RRF → batches flattened with cross-query point-id dedup → `(Document, score)` tuples formatted.
**Invariant:** (1) The CALLER never branches on provider identity — capability flags decide which fields ride the request; a provider that gains sparse support needs zero retrieval-code changes. (2) Sparse vectors are sent ONLY to stores that index them client-side; text goes ONLY to stores with server-side BM25 — sending both would double-count relevance. (3) RRF fusion is declared per-request, not configured per-store, so mixed fleets stay comparable. (4) Dedup is by POINT ID across all query batches, first-wins, before formatting — multi-query expansion must not return the same chunk twice. (5) No dense embeddings is a hard ValueError, not an empty result (test :451–454 pins the raise).
**Probe:** EXECUTED at pin: `/tmp/psh21venv/bin/python -m pytest tests/unit/modules/retrieval/test_retrieval_service.py -p no:warnings` → suite green (combined battery 124 passed / 0 failed, rc=0, 2.61s). Decisive tests: `TestExecuteParallelSearches` test_raises_without_dense_embeddings :451–454, test_skips_sparse_when_provider_does_not_support_it :457–465, test_returns_formatted_results :468–486 (asserts list-of-lists API + score/content passthrough), test_deduplicates_points :489–505 ([[point],[point]] ⇒ 1 result).
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*modules/retrieval/*` query="_execute_parallel_searches HybridSearchRequest RRF fusion" → resolves `RetrievalService._execute_parallel_searches` (graph rows show stale offsets :752–818; HEAD truth is :798–864 — source wins).

## Verdict
Adopt the capability-flag-gated single request-builder whenever one service fronts heterogeneous vector stores; adopt per-request fusion declaration and cross-query id-dedup verbatim. Adapt the two capability flag names to your provider registry. Omit the parallel dense+sparse gather only if your embedders are cheap — the gating itself is never optional.
