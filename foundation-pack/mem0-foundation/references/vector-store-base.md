<!-- capsule-v2 -->
# Vector store base — the storage-backend ABC contract

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory system abstract any vector store (Qdrant, Pinecone, Chroma, etc.) behind one ABC?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/base.py`: `VectorStoreBase` (:4) — `create_col` (:6), `insert` (:11), `search` (:16), `delete` (:29), `update` (:34), `get` (:39), `list_cols` (:44), `delete_col` (:49), `col_info` (:54), `list` (:59), `reset` (:64), `keyword_search` (:68), `search_batch` (:85).
**Signature:** `search(query, vectors, top_k=5, filters=None)` — vector similarity search with optional metadata filters; `insert(vectors, payloads=None, ids=None)` — bulk insert with optional payloads/ids; `keyword_search(query, top_k=5, filters=None)` — lexical fallback.
**Data Shape:** the ABC defines the contract; each backend (`qdrant.py`, `pinecone.py`, `chroma.py`, `pgvector.py`, etc.) implements it; `filters` translate via `vector_stores/filters.py`.

### Decisive source
```ts
class VectorStoreBase(ABC):
    def create_col(self, name, vector_size, distance): ...
    def insert(self, vectors, payloads=None, ids=None): ...
    def search(self, query, vectors, top_k=5, filters=None): ...
    def keyword_search(self, query, top_k=5, filters=None): ...
    def search_batch(self, queries, vectors_list, top_k=1, filters=None): ...
```

**Flow:** the memory layer calls the ABC methods; each backend implements the same contract (create/insert/search/delete/update/list/reset + keyword_search + search_batch). Filters are translated per-backend so metadata queries work across stores.
**Invariant:** every backend implements the full ABC (a missing method breaks the memory layer); `search_batch` handles multiple queries in one call.
**Probe:** `tests/memory/` backend tests (each backend implements create/insert/search; filters translate; keyword_search fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "VectorStoreBase create_col insert search keyword_search backend", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the vector-store ABC contract (create/insert/search/delete/list + keyword/search_batch); adapt the backend implementations and filter translation to host.
