<!-- capsule-v2 -->
# Kuzu edge-as-node — modeling relationships when the DB can't index edge properties

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how do you port a property-graph schema to a database whose edges can't carry fulltext-indexed properties, without changing any calling code?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/models/edges/edge_db_queries.py:get_entity_edge_save_query` KUZU branch (:84–102) + `get_entity_edge_return_query` KUZU branch (:199–214) incl. direction comment (:191–197); `graphiti_core/graph_queries.py` `INDEX_TO_LABEL_KUZU_MAPPING` ('edge_name_and_fact' → 'RelatesToNode_', :20–25).
**Signature:** save/return builders take `provider: GraphProvider`; the Kuzu branches swap `(a)-[e:RELATES_TO]->(b)` for a two-hop node chain.
**Data Shape:** every `EntityEdge` is stored as an intermediate NODE `RelatesToNode_` plus TWO directed `:RELATES_TO` edges; all edge properties live on that node as plain columns (`attributes` included), which is what makes `CREATE_FTS_INDEX('RelatesToNode_', ...)` possible.

### Decisive source
```python
case GraphProvider.KUZU:
    return """
        MATCH (source:Entity {uuid: $source_uuid})
        MATCH (target:Entity {uuid: $target_uuid})
        MERGE (source)-[:RELATES_TO]->(e:RelatesToNode_ {uuid: $uuid})-[:RELATES_TO]->(target)
        SET e.group_id = $group_id, e.created_at = $created_at, ...
        RETURN e.uuid AS uuid
    """
# get_entity_edge_return_query docstring (:191-197): NEO4J/FALKORDB/NEPTUNE read
# source/target via startNode(e)/endNode(e) off the relationship itself;
# Kuzu's MATCH is always directed, so n/m already ARE true source/target and
# startNode/endNode are not applicable to a node.
```

**Flow:** same Python call → provider switch → Kuzu materializes the fact as a node between the two entities; reads MATCH through the chain so record keys stay identical (`source_node_uuid`, `target_node_uuid`); fulltext/vector indexes target the node label like any other entity.
**Invariant:** (1) return-query column names must NOT change across providers — parsers are shared, only query text differs (that's why Kuzu returns `n.uuid AS source_node_uuid` where Neo4j returns `startNode(e).uuid AS source_node_uuid`); (2) MERGE key stays `{uuid: $uuid}` so re-saving the same edge updates rather than duplicates; (3) undirected MATCHes elsewhere in the codebase still work because traversal follows real edges — but ranking/index code must use `RelatesToNode_` label lookups.
**Probe:** `tests/test_edge_db_queries.py:38 test_kuzu_keeps_match_variables` (pins n/m variables, forbids startNode/endNode, pins `e.attributes AS attributes`); `tests/test_edge_int.py` round-trips.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "RelatesToNode_ Kuzu entity edge save return", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the edge-as-node pattern whenever a backend can't index edge properties (keep column names stable); adapt the label name and DDL; omit the other three providers' branches if you only port one engine — but keep the single shared parser contract.
