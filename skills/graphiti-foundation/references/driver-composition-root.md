<!-- capsule-v2 -->
# Driver composition-root — capability properties, feature-detect, transaction wrapper

**Source:** graphiti Apache-2.0 `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how does a graph driver compose per-node/edge operations mixins and expose transactions so callers never bind to a concrete dialect?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/driver.py:GraphDriver` (:90–211), `_SessionTransaction` (:213–222); `graphiti_core/driver/query_executor.py` (`QueryExecutor`, `Transaction`); `graphiti_core/driver/falkordb_driver.py:FalkorDriver` (:127–375).
**Signature:** `GraphDriver(QueryExecutor, ABC)` with 11 capability `@property` accessors (`entity_node_ops`, `episode_node_ops`, `community_node_ops`, `saga_node_ops`, `entity_edge_ops`, `episodic_edge_ops`, `community_edge_ops`, `has_episode_edge_ops`, `next_episode_edge_ops`, `search_ops`, `graph_ops`); `@asynccontextmanager async def transaction() -> AsyncIterator[Transaction]`.
**Data Shape:** the base class returns `None` from every capability property by default — so a caller must feature-detect (`if driver.entity_node_ops is not None:`) rather than assume support. Concrete drivers instantiate the dialect-specific ops objects in `__init__` and override the properties to return them. `transaction()` yields a `Transaction` with a single `async run(query, **kwargs)`; the base implementation wraps a session (`_SessionTransaction`) so queries execute immediately (auto-commit), while Neo4j overrides it for native commit/rollback.

### Decisive source
```python
# driver.py
class GraphDriver(QueryExecutor, ABC):
    @property
    def entity_node_ops(self) -> EntityNodeOperations | None:
        return None          # default: feature-detect, not assume

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Transaction]:
        session = self.session()
        try:
            yield _SessionTransaction(session)   # auto-commit fallback
        finally:
            await session.close()

class _SessionTransaction(Transaction):
    async def run(self, query: str, **kwargs: Any) -> Any:
        return await self._session.run(query, **kwargs)
```
```python
# falkordb_driver.py — concrete driver composes mixins in __init__
self._entity_node_ops = FalkorEntityNodeOperations()
# ... 11 ops objects ...
@property
def entity_node_ops(self) -> EntityNodeOperations:
    return self._entity_node_ops
```

**Flow:** base `GraphDriver` defines the contract (feature-detect `None` ops, auto-commit transaction) → each concrete driver (Falkor/Neo4j/Kuzu/Neptune) instantiates its dialect ops mixins in `__init__` and overrides the properties → callers use `async with driver.transaction() as tx:` and pass `tx` into ops methods (`await ops.save(driver, node, tx=tx)`); drivers with real transactions commit on clean exit / roll back on exception, others execute immediately.
**Invariant:** (1) the capability properties are the ONLY way callers reach ops — a `None` return means "not supported," never "empty"; (2) the `Transaction` interface is a single `run()` — no dialect-specific transaction API leaks to callers; (3) the base `transaction()` must always close its session even on exception (finally). `with_database()`/`clone()` return shallow copies reusing the same connection.
**Probe:** `tests/driver/test_falkordb_ops_routing.py` (pins that `FalkorDriver.entity_node_ops` returns the Falkor ops instance and routes correctly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "GraphDriver entity_node_ops transaction _SessionTransaction GraphProvider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capability-property + feature-detect pattern and the single-`run()` Transaction interface (they decouple callers from dialect); adapt the concrete ops mixin wiring to your provider; omit the auto-commit `_SessionTransaction` fallback if your DB has real transactions — override `transaction()` instead. Coverage caveat: `test_falkordb_ops_routing.py` pins the Falkor wiring; the other three dialects' wiring is asserted by the same pattern but not each individually probed here.
