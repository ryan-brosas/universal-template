<!-- capsule-v2 -->
# Vector store degradation — Qdrant knowledge base that survives an unconfigured deployment

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do you structure vector upsert/search/delete so a missing embedding provider or dead Qdrant degrades the FEATURE instead of failing the pipeline?

## Chunk budget → embed-or-skip → delete-then-upsert
**Path/Symbol:** `backend/app/services/vector_store.py` whole (146L): `ensure_collection` :25–40 (409-tolerant create), `upsert_company_vectors` :42–61, `search_companies` :63–88, `get_similar_company_ids` :90–131 (centroid similarity), `delete_company_vectors` :133–140; caller `_run_vectorize` in `tasks/process.py` :582–728 (`_chunk_text` :33, 20-chunk cap, uuid5 point ids).
**Signature:** `VectorStore.upsert_company_vectors(company_id: str, chunks: list[dict])`; `get_similar_company_ids(company_id: str, top_k: int = 3) -> list[str]`.
**Data Shape:** Point payload `{company_id, text, chunk_index, category}`; point id = `uuid5(NAMESPACE_URL, f"georank:{company_id}:{i}")` — deterministic per company+position.

### Decisive source
```python
# process.py _run_vectorize — the degradation ladder:
try:
    vectors = await ai_client.embed_batch(selected_chunks)
except EmbeddingNotConfiguredError:
    vectors = []
    log_event(logger, logging.WARNING, "task.vectorize_company.embedding_skipped", ...)
if vectors and len(vectors) != len(selected_chunks):
    raise RuntimeError(f"Embedding 返回数量不完整：...")   # partial batch = hard error, never silent truncation
...
vector_store.ensure_collection()
vector_store.delete_company_vectors(company_id)     # replace-set semantics
vector_store.upsert_company_vectors(company_id, points)
```
Centroid similarity for "companies like this one":
```python
vectors = [p.vector for p in scroll_result if p.vector]
centroid = np.mean(vectors, axis=0).tolist()
results = client.search(query_vector=centroid, limit=top_k + 5)   # over-fetch then dedupe by company_id
```

**Flow:** word-chunk with 50-word overlap → cap 20 chunks → embed (missing config ⇒ empty vectors, log-and-continue; count mismatch ⇒ fail) → ensure collection (concurrent-create 409 swallowed when message contains "already exists") → delete company's old points by filter THEN upsert new set → RAG search filters on published companies at the DB layer afterward.
**Invariant:** A company's vector set is always the complete replacement of its latest run, or absent entirely — no partial mixes. Embedding-unavailable is a WARNING-level feature skip (pipeline still completes), while a MISMATCHED embed response is a hard failure (data integrity).
**Probe:** `backend/tests/test_vector_store.py::test_*` (mocked client contract incl. 409-tolerant creation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "delete_company_vectors", limit: 5 });
// verified line-exact: vector_store.py :133–140
```

## Verdict
Adopt skip-vs-fail degradation matrix and replace-set upserts for any RAG ingestion; adapt chunking to your tokenizer; omit numpy centroid if you don't need similar-company. Direct tests green under real runner.
