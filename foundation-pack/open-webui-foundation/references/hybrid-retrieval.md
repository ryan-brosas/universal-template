<!-- capsule-v2 -->
# Hybrid retrieval ladder — how do BM25 and vector search fuse under a reranker, degrading gracefully when the vector store lacks native hybrid?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** What runs before the legacy ensemble path, what deduplicates fused results, and which failures must fall back instead of raising?

## Native-first ladder with content-hash RRF dedup
**Path/Symbol:** `backend/open_webui/retrieval/utils.py:_supports_native_hybrid_search` (395-399), `query_doc_with_native_hybrid_search` (402-462), `query_doc_with_hybrid_search` (465-593).
**Signature:** `async def query_doc_with_hybrid_search(collection_name, collection_result, query, embedding_function, k, reranking_function, k_reranker, r, hybrid_bm25_weight, enable_enriched_texts=False, native_hybrid_search=True) -> dict`.
**Data Shape:** result is a GetResult dict `{'distances': [[...]], 'documents': [[...]], 'metadatas': [[...]]}`; scores ride in `metadata['score']`; every BM25 metadata gets `CHUNK_HASH_KEY = _content_hash(original_text)` used as the EnsembleRetriever `id_key`.

### Decisive source
```python
except Exception as e:
    log.debug(f'Native hybrid search failed for {collection_name}, '
              'falling back to legacy hybrid search: {e}')
    return None          # caller falls through to the legacy path

# legacy ensemble: weight edges collapse to a single retriever
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_search_retriever],
    weights=[hybrid_bm25_weight, 1.0 - hybrid_bm25_weight],
    id_key=CHUNK_HASH_KEY,   # hash of ORIGINAL text so enriched BM25
)                            # texts don't defeat RRF dedup

# retrieve only min(k, k_reranker): sort by score desc and cut if k < k_reranker
if k < k_reranker:
    sorted_items = sorted(zip(distances, documents, metadatas), key=lambda x: x[0], reverse=True)[:k]
```
**Flow:** native attempt first (skipped when `enable_enriched_texts`) → `None` (unsupported, no result, or any exception) falls through → fetch full collection, short-circuit empty to the empty GetResult shape → build BM25Retriever over original/enriched texts with hashed metadatas + VectorSearchRetriever → weighted EnsembleRetriever (`<=0` vector-only, `>=1` bm25-only) → RerankCompressor(`top_n=k_reranker, r_score=r`) via ContextualCompressionRetriever → trim to `k` by score desc. The native path embeds the query only when `hybrid_bm25_weight < 1`.
**Invariant:** a native-hybrid failure is logged at debug and degrades to the legacy path — never propagated; an empty collection returns the empty shape rather than raising; fusion dedup keys on the original chunk-content hash so enriched BM25 texts cannot inflate RRF; the final list respects `min(k, k_reranker)` even when reranking asked for more.
**Probe:** no test runner at this HEAD — deterministic anchors executed: `grep -n "falling back to legacy hybrid search" backend/open_webui/retrieval/utils.py` hits line 461; `sed -n '416,418p' backend/open_webui/retrieval/utils.py` equals the `query_vectors` gate excerpt above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "query_doc_with_hybrid_search EnsembleRetriever RerankCompressor fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the native-first-then-fallback control flow, content-hash RRF dedup key, weight-edge degenerate ensembles, and the k/k_reranker trim algebra; adapt the LangChain retriever classes and per-backend `hybrid_search` clients to your stack; omit open-webui's specific provider matrix (pgvector/mariadb/qdrant/...). Coverage caveat: none recorded for these paths; direct tests absent repo-wide.
