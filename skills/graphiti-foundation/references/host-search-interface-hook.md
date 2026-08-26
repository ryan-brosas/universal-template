<!-- capsule-v2 -->
# SearchInterface custom-search hook — provider fast-path, host override

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how do you let a HOST application inject its own search implementations without forking the driver layer?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/search_interface/search_interface.py:SearchInterface` (BaseModel, all-Any-typed methods); consumption `graphiti_core/search/search.py` + `search_config_recipes` via `driver.search_interface` first, generic Cypher fallback; contrast with typed sibling `driver/operations/search_ops.py:SearchOperations` (ABC).
**Signature:** `class SearchInterface(BaseModel)` — plain async methods (`edge_fulltext_search`, `edge_similarity_search`, `node_bfs_search`, ...) with `Any` hints; NOT abstractmethods, so partial overrides are legal.
**Data Shape:** docstring type reference maps Any → GraphDriver / SearchFilters / node & edge models "to avoid circular imports"; pydantic BaseModel base gives it config validation + deprecation warnings (PydanticDeprecatedSince20 on class-based config at :22).

### Decisive source
```python
# search_interface.py :21-28
class SearchInterface(BaseModel):
    """
    Interface for implementing CUSTOM search logic.

    All methods use `Any` type hints to avoid circular imports. See docstrings
    for expected concrete types.
    """
    # plain async defs — a host subclasses and implements ONLY what it
    # customizes; unimplemented methods are inherited no-ops, not errors.
```

**Flow:** search primitives check `driver.search_interface` BEFORE issuing generic Cypher (provider fast-path) → hosts assign their own SearchInterface subclass onto the driver to intercept specific primitives (e.g. replace similarity search with a hosted vector service) while leaving fulltext/BFS defaults intact → NotImplementedError-style fallbacks stay in the CALLER (search.py), not the interface.
**Invariant:** (1) this is the HOST-extension surface, deliberately distinct from `SearchOperations` (the DRIVER-author ABC where every method is @abstractmethod and backends must implement all); (2) BaseModel-with-Any-methods is a deliberate pydantic trick — instances ride on the driver as validated fields while method bodies stay duck-typed; (3) partial implementation is the point: overriding two of eight primitives is a supported configuration, unlike the ops layer.
**Probe:** `cd /mnt/hdd/utopia/inspo/memory/graphiti && grep -c '@abstractmethod' graphiti_core/driver/search_interface/search_interface.py` → `0`; `grep -c '@abstractmethod' graphiti_core/driver/operations/search_ops.py` → `14`; direct tests: none target this class directly (coverage caveat — exercised indirectly through driver.search_interface consumers in tests/utils/search/).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "SearchInterface custom search logic driver.search_interface", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the twin-surface split (strict ABC for backend authors, open BaseModel hook for application authors) whenever one extension point serves two audiences with different obligations; adapt method inventory to your primitive set. Porters who merge them either force hosts to implement everything or let drivers silently skip required methods.
