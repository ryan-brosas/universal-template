<!-- capsule-v2 -->
# Graph driver — the provider-agnostic graph DB abstraction

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does a temporal knowledge-graph system abstract Neo4j/FalkorDB/Kuzu/Neptune behind one driver?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/driver.py`: `GraphProvider` (:59), `GraphDriverSession` (:66), `GraphDriver` (:90) — `execute_query` (:102), `session` (:106), `build_indices_and_constraints` (:128), `transaction` (:147), `entity_node_ops`/`episode_node_ops`/`community_node_ops` (:169-177); providers `neo4j_driver.py`, `falkordb_driver.py`, `kuzu_driver.py`, `neptune_driver.py`.
**Signature:** `GraphDriver.execute_query(cypher_query_, **kwargs)` — runs a Cypher query; `session()` returns a `GraphDriverSession` (async context manager with `run`/`execute_write`); `transaction()` yields a `Transaction`.
**Data Shape:** `GraphProvider` enum (NEO4J/FALKORDB/KUZU/NEPTUNE); each provider implements `GraphDriver`; node operations exposed via `entity_node_ops`/`episode_node_ops`/`community_node_ops`.

### Decisive source
```ts
class GraphDriver(QueryExecutor, ABC):
    def execute_query(self, cypher_query_, **kwargs): ...
    def session(self, database=None) -> GraphDriverSession: ...
    def transaction(self) -> AsyncIterator[Transaction]: ...
    def entity_node_ops(self): ...
    def episode_node_ops(self): ...
    def community_node_ops(self): ...
```

**Flow:** the memory layer runs Cypher queries via `execute_query` / sessions / transactions; each provider (Neo4j/FalkorDB/Kuzu/Neptune) implements the same `GraphDriver` contract; node operations (entity/episode/community) are exposed per-driver.
**Invariant:** every provider implements the full `GraphDriver` contract (queries, sessions, transactions, indices, node ops); queries are Cypher across providers.
**Probe:** `tests/` driver tests (each provider executes a query; session/transaction; build_indices_and_constraints; node ops).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "GraphDriver execute_query session transaction node ops provider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the graph-driver ABC (Cypher queries, sessions, transactions, node ops) with pluggable providers; adapt the provider backends and query dialect to host.
