<!-- capsule-v2 -->
# Typed ops ABC layer — capability properties, batch_size=100, uuid cursor

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** what is the concrete contract a driver author must satisfy to add a backend, and which "obvious" defaults are actually load-bearing?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/operations/` — `entity_node_ops.py:EntityNodeOperations` (103L), `episode_node_ops.py` (107L), `community_node_ops.py` (95L), `entity_edge_ops.py` (108L), `episodic_edge_ops.py` (78L), `community_edge_ops.py` (69L), `saga_node_ops.py` (88L), `has_episode_edge_ops.py` (78L), `next_episode_edge_ops.py` (78L), `search_ops.py:SearchOperations` (165L), `graph_ops.py:GraphMaintenanceOperations` (94L); capability accessors `graphiti_core/driver/driver.py:entity_node_ops/.../graph_ops` (:169-210); FalkorDB reference impl `driver/falkordb/operations/entity_node_ops.py`.
**Signature:** every op takes `executor: QueryExecutor` FIRST plus optional `tx: Transaction | None = None` — write ops run through `tx.run(query, ...)` when a tx is handed in, else `executor.execute_query(...)`; reads take only executor.
**Data Shape:** 11 ABCs × ~10 abstractmethods; the base `GraphDriver` returns `None` from EVERY ops property (:169-210) so "capability absent" is representable; `get_by_group_ids(..., limit: int | None = None, uuid_cursor: str | None = None)` is the pagination surface.

### Decisive source
```python
# operations/entity_node_ops.py :33-39
async def save_bulk(self, executor, nodes,
                    tx: Transaction | None = None,
                    batch_size: int = 100) -> None: ...
# falkordb/operations/entity_node_ops.py :57-58 (the porter's trap)
async def save_bulk(self, executor, nodes,
                    tx=None,
                    batch_size: int = 100,   # noqa: ARG002
                    ) -> None:
    ...
    queries = get_entity_node_save_bulk_query(GraphProvider.FALKORDB, prepared)
    for query, params in queries:            # builder ALREADY chunked Falkor's
        if tx is not None:                   # UNWIND into label-partitioned
            await tx.run(query, **params)    # multi-label queries — the ABC's
        else:                                # batch_size is deliberately IGNORED
            await executor.execute_query(query, **params)
```

**Flow:** caller asks `driver.entity_node_ops` → `None` means feature unsupported (never an empty result) → concrete ops execute dialect queries with params built per node (`entity_data.update(node.attributes or {})`, labels normalized `set(labels + ['Entity'])`) → Falkor bulk path delegates chunking to the query builder and iterates returned `(query, params)` tuples.
**Invariant:** (1) `tx` presence switches execution but NEVER semantics — same query either way; (2) the ABC declares `batch_size=100` on save/delete/load_embeddings_bulk, but the FalkorDB impl marks it `noqa: ARG002` and ignores it because `*_save_bulk_query` pre-chunks by label partition — copying the default without checking your builder's contract silently changes memory profile; (3) `get_by_uuid` raises `NodeNotFoundError` on zero records while `get_by_uuids` returns [] — singular vs plural asymmetry is API; (4) `delete_by_group_id`/`delete_by_uuids` also carry ignored `batch_size` params (interface symmetry over behavior); (5) pagination is keyset (`AND n.uuid < $uuid` + `ORDER BY n.uuid DESC` + LIMIT), not offset.
**Probe:** `cd $REFERENCE_ROOT/memory/graphiti && grep -c 'batch_size: int = 100' graphiti_core/driver/operations/entity_node_ops.py` → `4`; `grep -c 'batch_size: int = 100' graphiti_core/driver/falkordb/operations/entity_node_ops.py` → `4`; `grep -c 'noqa: ARG002' graphiti_core/driver/falkordb/operations/entity_node_ops.py` → `4`; `grep -c 'uuid_cursor: str | None = None' graphiti_core/driver/operations/entity_node_ops.py` → `1`; direct tests `tests/driver/test_falkordb_driver.py` + routing pins in `tests/driver/test_falkordb_ops_routing.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "EntityNodeOperations save_bulk Transaction QueryExecutor abstract", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the executor-first + optional-tx op signature and the None-means-unsupported capability property pattern when porting any dialect layer; adapt method inventory to your node/edge kinds; do NOT copy `batch_size=100` into an implementation whose query builder already chunks — audit who owns chunking first. Coverage caveat: no unit test asserts the ignore-batch_size behavior directly; pinned by source read at :57-79.
