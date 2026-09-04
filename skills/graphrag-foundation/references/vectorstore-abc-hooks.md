<!-- capsule-v2 -->
# VectorStore ABC template-method split — which lifecycle hooks does the base class own so a new backend implements only storage mechanics?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** where is the line between base-class-provided behavior and backend-required methods in this vector-store abstraction?

## VectorStore abstract surface
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/vector_store.py` (`VectorStore` :56-217, `VectorStoreDocument` :25-42, `VectorStoreSearchResult` :45-53).
**Signature:** ABSTRACT: `connect/create_index/load_documents/similarity_search_by_vector/search_by_id/count/remove/update`. CONCRETE: `insert` (delegates to `load_documents([doc])` :147-149), `similarity_search_by_text` (embeds then delegates; EMPTY embedding → returns `[]` not error :176-195), `_prepare_document`/`_prepare_update` (timestamp hooks), `_now_iso` static.
**Data Shape:** `VectorStoreDocument{id: str|int, vector: list[float]|None, data: dict, create_date/update_date: str|None}`; search returns `{document, score: float(-1..1)}`.

### Decisive source
```python
# vector_store.py:186-195 — text-search degrades to NO RESULTS on empty
# embedding instead of raising; callers cannot distinguish "no matches"
# from "embedder returned nothing" — a deliberate fail-open for pipelines
query_embedding = text_embedder(text)
if query_embedding:
    return self.similarity_search_by_vector(...)
return []
```
```python
# __init__ kwargs are the FULL config surface every backend must accept:
index_name="vector_index", id_field="id", vector_field="vector",
create_date_field="create_date", update_date_field="update_date",
vector_size=3072, fields=None, timestamp_exploder=explode_timestamp, **kwargs
```

**Flow:** factory constructs store with merged config+schema kwargs (see singleton-service-factory capsule) → `connect()` → `create_index()` → per-doc: `_prepare_document` mutates data dict with exploded timestamps THEN backend `load_documents` persists (the docstring says "call during insert before extracting field values") → queries via by_vector/by_text/by_id; updates MUST call `_prepare_update` first or update_date components go stale.
**Invariant:** backends that override `load_documents` without calling `_prepare_document` lose ALL timestamp filtering silently; `include_vectors` defaults True everywhere (porters flipping it to False-by-default break embed-text reconstitution flows); `search_by_id` raises/returns-None is BACKEND-defined (LanceDB raises IndexError on miss — callers wrap it, see indexer-adapters capsule).
**Probe:** no dedicated unit suite for vector_store.py itself (abstract); behavior pinned through `tests/unit/vector_stores/test_timestamp.py` (registration contract :74-112) and LanceDB integration coverage. Recorded caveat: base-class hooks verified by source read + consumer greps, not a direct test file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "VectorStore similarity search by text prepare document timestamp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the concrete-hook placement (insert→load_documents delegation, empty-embedding→empty-results, write-time timestamp prep); adapt field names/defaults to host schema; omit CosmosDB/AzureAISearch implementations unless targeting those backends.
