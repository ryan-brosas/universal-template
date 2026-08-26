<!-- capsule-v2 -->
# Storage / cache / vector-store ABC trio — swappable backends with child scoping

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does an indexing pipeline stay backend-agnostic (local disk vs blob vs cosmos) across three storage layers at once?

## Connected graph-selected seam
**Path/Symbol:** `graphrag_storage/storage.py`: `Storage` (ABC) — `find(pattern)` (:24), `get(key, as_bytes?, encoding?)`, `set(key, value, encoding?)`, `has`, `delete`, `clear`, `child(name)`, `keys()`, `get_creation_date`; backends `file_storage.py`, `azure_blob_storage.py` (:23), `azure_cosmos_storage.py` (:34); `tables/` providers (csv/parquet/cosmos). `graphrag_cache`: `Cache` ABC + `memory_cache`/`json_cache`/`noop_cache` + `cache_factory`. `graphrag_vectors`: `VectorStore` ABC (`vector_store.py`) + `azure_ai_search.py`/`cosmosdb.py` + `index_schema.py`.
**Signature:** `child(name)` — derives a namespaced sub-storage from the parent (FileStorage appends a path segment; Cosmos prefixes the key); every backend implements the identical 9-method surface.
**Data Shape:** values are str|bytes with explicit `encoding`; keys are flat strings (backends map them to path/blob/partition-key); table providers add typed read/write over the same backends.

### Decisive source
```ts
class Storage(ABC):
    def find(self, file_pattern: re.Pattern[str]) -> Iterator[str]: ...
    async def get(self, key, as_bytes=None, encoding=None): ...
    async def set(self, key, value, encoding=None): ...
    def child(self, name): ...   # scope narrowing
# FileStorage.child:
def child(self, name):
    if name is None: return self
    return FileStorage(base_dir=self._base_dir / name, encoding=self._encoding)
```

**Flow:** pipeline code receives one `Storage` per output class (artifacts, reports, output) → all reads/writes/list go through the ABC → a step needing its own folder calls `.child("step_name")` instead of building paths → swapping local disk for Azure blob changes only config. The same shape repeats for `Cache` (with a Noop variant making "caching off" free) and `VectorStore` (with `index_schema` defining the record layout).
**Invariant:** no backend-specific calls leak into the pipeline; child() must preserve encoding/config of the parent; Noop implementations exist so disabling a layer costs nothing.
**Probe:** `tests/` storage tests (file/blob parity via shared suite; child() nesting; find() pattern filtering; cache factory returns noop when disabled).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "Storage child FileStorage AzureBlobStorage Cache VectorStore factory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the triple-ABC storage design (key-value Storage, Cache with Noop, VectorStore) plus child()-based scoping so pipelines never touch paths or cloud SDKs directly.
