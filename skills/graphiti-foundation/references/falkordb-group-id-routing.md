<!-- capsule-v2 -->
# FalkorDB per-group-id graph routing — clone-to-group-or-empty-result

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when a graph backend physically partitions tenants into separate databases/graphs, how do read paths stay correct without leaking that partitioning into every caller?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/falkordb/operations/entity_node_ops.py:FalkorEntityNodeOperations.get_by_group_ids` (:185-229); same routing block in `episode_node_ops.py`, `entity_edge_ops.py`, `community_node_ops.py`, `saga_node_ops.py` (per-file copies); decorator-level twin `graphiti_core/decorators.py:handle_multiple_group_ids` (:58-69).
**Signature:** `async get_by_group_ids(executor: QueryExecutor, group_ids: list[str], limit: int | None = None, uuid_cursor: str | None = None) -> list[EntityNode]`.
**Data Shape:** FalkorDB stores each `group_id` in its OWN physical graph database; a group-scoped read against the base driver (pointed at `default_db`) queries an EMPTY database and silently returns `[]`.

### Decisive source
```python
# falkordb/operations/entity_node_ops.py :185-204
# For FalkorDB, route each group_id to its own graph database. The
# namespace/ops path receives the base driver (default_db), so a
# single-group read must be cloned to the group's graph or it queries
# an empty default database and returns nothing.
if (
    isinstance(executor, GraphDriver)
    and executor.provider == GraphProvider.FALKORDB
    and group_ids                      # truthy gate: [] falls through to generic path
):
    if len(group_ids) == 1:
        executor = executor.clone(database=group_ids[0])   # rebind LOCAL name only
    else:
        all_nodes: list[EntityNode] = []
        for gid in group_ids:
            partial = await self.get_by_group_ids(
                executor.clone(database=gid), [gid], limit, uuid_cursor
            )
            all_nodes.extend(partial)
        all_nodes.sort(key=lambda n: n.uuid, reverse=True)  # merge must match
        if limit is not None:                               # single-graph ORDER
            all_nodes = all_nodes[:limit]
        return all_nodes
```

**Flow:** guard on (executor is a GraphDriver) ∧ (provider==FALKORDB) ∧ truthy group_ids → single group: `clone(database=gid)` replaces the LOCAL executor binding and runs the normal query against that graph → multiple groups: recurse per group on a fresh clone, extend, then re-sort merged results by uuid DESC so pagination semantics match the single-graph query (`ORDER BY n.uuid DESC` + `AND n.uuid < $uuid` cursor + optional `LIMIT $limit`) → any other provider or empty list: fall through to the generic `WHERE n.group_id IN $group_ids` Cypher untouched.
**Invariant:** (1) the clone is CALL-SCOPED — `executor = executor.clone(...)` never mutates the shared driver object callers hold; (2) an empty `group_ids` list means "no scoping requested" and MUST NOT route (cloning would query a literally-named empty graph); (3) multi-group fan-out must reproduce the single-graph ordering (sort DESC by uuid) BEFORE applying limit, or deep pages drift between providers; (4) routing is provider-gated so the same ops class stays portable to Neo4j where group_id is just a property.
**Probe:** `cd /mnt/hdd/utopia/inspo/memory/graphiti && grep -c 'executor.clone(database=gid)' graphiti_core/driver/falkordb/operations/entity_node_ops.py` → `1`; `grep -c 'all_nodes.sort(key=lambda n: n.uuid, reverse=True)' graphiti_core/driver/falkordb/operations/entity_node_ops.py` → `1`; direct tests `tests/driver/test_falkordb_ops_routing.py::test_episode_get_by_group_ids_single_group_routes_to_its_graph` (:55, pins `base.clone.assert_called_once_with(database='group-a')` AND `base.execute_query.assert_not_called()`), `test_get_by_group_ids_empty_group_ids_does_not_route` (:111).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "get_by_group_ids clone database route group graph Falkor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt call-scoped executor cloning as the tenant-routing pattern for physically-partitioned backends; adapt the merge sort key to your canonical page order; omit the isinstance/provider guard only if your host has exactly one partitioned backend. A porter who clones the SHARED driver instead of the local binding corrupts every subsequent caller.
