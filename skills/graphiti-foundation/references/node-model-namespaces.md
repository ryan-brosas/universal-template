<!-- capsule-v2 -->
# Node model & namespaces — graph-idiom delete + typed data access

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do node models encapsulate provider-specific deletes, and how do namespaces give typed CRUD over each node kind?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/nodes.py` (1,122 lines): `Node` (:93), `validate_labels` (:104), `delete` (:111-166), `EpisodeType` (:54), `delete_by_group_id` (:178), `delete_by_uuids` (:237); `graphiti_core/namespaces/nodes.py` (355 lines): `EntityNodeNamespace` (:29) — save/save_bulk/delete/get_by_uuid(s)/get_by_group_ids/load_embeddings(_bulk); `namespaces/edges.py` (355 lines) mirrors it for edges.
**Signature:** `Node.delete(driver)` — tries `driver.graph_operations_interface.node_delete`, catches `NotImplementedError`, then matches `driver.provider`; `EntityNodeNamespace.load_embeddings_bulk(nodes)` hydrates embeddings in bulk.
**Data Shape:** `Node {uuid (uuid4 default), name, group_id, labels[], created_at=utc_now()}`, `model_config = ConfigDict(validate_assignment=True)`; labels validated by `validate_node_labels`.

### Decisive source
```ts
async def delete(self, driver):
    if driver.graph_operations_interface:
        try: return await driver.graph_operations_interface.node_delete(self, driver)
        except NotImplementedError: pass          # fall through to per-provider Cypher
    match driver.provider:
        case GraphProvider.NEO4J:
            # OPTIONAL MATCH (n)-[r]-() WITH collect(r.uuid) AS edge_uuids, n DETACH DELETE n
        case GraphProvider.KUZU:
            # Entity edges are actually NODES in Kuzu: delete RelatesToNode_ first,
            # then the entity node. Simple DETACH DELETE will not work.
        case _:  # FalkorDB, Neptune
            for label in ['Entity', 'Episodic', 'Community']: DETACH DELETE
```

**Flow:** the abstract `Node` base owns uuid/name/group_id/labels/created_at and a provider-matched delete; the interface fast-path runs first with a generic-Cypher fallback. Namespaces (`EntityNodeNamespace` etc.) wrap the driver ops into typed repositories: save/bulk-save, delete by uuid/group, fetch, and embedding hydration.
**Invariant:** Kuzu models entity-edges as nodes, so deletes must remove `RelatesToNode_` before the entity; every delete is DETACH (children handled); timestamps are UTC at creation.
**Probe:** `tests/` node tests (delete removes edges+node per provider; label validation rejects bad labels; namespace get_by_uuids/load_embeddings_bulk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "Node delete provider match Kuzu RelatesToNode_ EntityNodeNamespace load_embeddings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt model-owned provider-matched deletes behind an interface fast-path, plus namespace repositories for typed CRUD; adapt the provider cases and namespace surface to host.
