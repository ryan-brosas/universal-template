<!-- capsule-v2 -->
# Vector-store adapter contract + factory — which five methods must a RAG backend implement, and why does lexical search default to [] instead of raising?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You're defining the seam between a retrieval engine and its storage backends — what belongs in the interface, and how should hybrid (dense+lexical) degrade for backends without BM25?

## Engine talks ONLY through VectorStoreAdapter; search_lexical is a graceful-degradation default
**Path/Symbol:** `src/cuga/backend/knowledge/vector_store_base.py` — ABC :11-50: `add_documents` :14-26, `search` :28-30, `search_lexical` :32-42 (NOT abstract), `delete_by_source` :44-46, `drop` :48-50. Factory: `src/cuga/backend/knowledge/vector_store.py` — `create_vector_store` :27-99, `KNOWLEDGE_LOCAL_VECTORS_DB = "knowledge_vectors.db"` :24.
**Signature:** `add_documents(documents, stage_timings=None) -> {"num_added": N, "num_skipped": M}`; `search(query, k=10) -> list[(Document, float)]` scores in [0,1] higher-closer; `search_lexical(query, k=10) -> list[(Document, float)]` default `return []`; `delete_by_source(source_id)`; `drop()`.
**Data Shape:** `stage_timings` dict is an OPTIONAL out-parameter — implementations may populate per-stage timings (`embed_s`, `insert_s`) that the engine renders as a granular ingest progress bar; may be ignored.

### Decisive source
```python
# vector_store_base.py:32-42 — the load-bearing comment
def search_lexical(self, query, k=10):
    """...Default implementation returns [] — adapters that don't have
    a lexical index (or haven't backfilled an existing collection)
    degrade gracefully to dense-only when the engine fuses them. NOT
    abstract: adding a new adapter shouldn't be forced into
    implementing a BM25 index right away; [] is a correct answer
    for 'no lexical signal available.'"""
```
**Flow (factory):** `backend == "storage_local"` → mkdir persist_dir → adapter over `<persist_dir>/knowledge_vectors.db` (sqlite-vec) | `backend == "storage_prod"` → resolve Postgres URL from explicit arg OR settings (`get_storage_connection_params`), raise ValueError if neither | else ValueError. Batch knobs (`embedding_batch_size=64`, `embedding_concurrency=4`, `vector_insert_batch_size=200`) pass through to both.
**Invariant:** (1) Knowledge vectors live in their OWN sqlite file (`knowledge_vectors.db` under `knowledge.persist_dir`), NOT the shared `cuga.db` — config resets that delete the app DB must not wipe RAG vectors. (2) `metric_type` param is accepted-but-unused (API stability). (3) New-backend onboarding cost is exactly 5 methods, and lexical can wait — fusion treats `[]` as "no signal", not an error.

**Probe:** No direct unit suite for base/factory at HEAD (coverage caveat — both are thin composition layers exercised via engine/storage suites: `tests/unit/test_knowledge_local_add_many.py` pins the local adapter behavior; prod side pinned by integration test_knowledge_pgvector_rollback.py).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_vector_store storage_local storage_prod backend VectorStoreAdapter search_lexical", limit: 8 });
```
## Verdict
Adopt the five-method contract with optional-not-abstract degradation methods whenever a new capability axis (here: lexical) rolls out across multiple backends. Adapt file names. Omit the stage_timings channel if you have no progress UI.
