<!-- capsule-v2 -->
# add_triplet write path — resolve-or-create endpoints, merge-not-replace, uuid-collision guard

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when a caller writes one fact edge directly (no episode extraction), how do the endpoint nodes get reconciled with existing entities and what user-supplied fields survive?

## Direct triplet write path
**Path/Symbol:** `graphiti_core/graphiti.py`: `add_triplet` (:1645-1763); embeddings-first (:1648-1653); get-by-uuid else resolve ladder per endpoint (:1655-1672); field merge rules (:1675-1692); edge-uuid collision guard (:1697-1715); synthetic episode + shared resolver reuse (:1721-1755).
**Signature:** `async add_triplet(self, source_node: EntityNode, edge: EntityEdge, target_node: EntityNode) -> AddTripletResults`.
**Data Shape:** caller may pass only names (MCP builds fresh uuid4 entities) or full objects with uuids; a synthetic `EpisodicNode` is fabricated so the SAME `resolve_extracted_edge` dedup machinery runs unchanged.

### Decisive source
```python
# Endpoint ladder: exact uuid hit wins; NodeNotFoundError -> name-based
# resolution/dedup via resolve_extracted_nodes([node]) -> canonical node.
try:
    resolved_source = await EntityNode.get_by_uuid(self.driver, source_node.uuid)
except NodeNotFoundError:
    resolved_source_nodes, _, _ = await resolve_extracted_nodes(self.clients, [source_node])
    resolved_source = resolved_source_nodes[0]

# User fields MERGE into the resolved node — never replace:
if source_node.attributes:
    resolved_source.attributes.update(source_node.attributes)   # dict update
if source_node.summary:
    resolved_source.summary = source_node.summary               # non-empty wins
if source_node.labels:
    resolved_source.labels = list(set(resolved_source.labels) | set(source_node.labels))

# Edge-uuid reuse across DIFFERENT endpoints would silently overwrite history
# -> mint a NEW uuid instead of updating in place:
existing_edge = await EntityEdge.get_by_uuid(self.driver, edge.uuid)
if (existing_edge.source_node_uuid != edge.source_node_uuid
        or existing_edge.target_node_uuid != edge.target_node_uuid):
    edge.uuid = str(uuid4())
```

**Flow:** ensure all three embeddings exist → reconcile both endpoints (uuid lookup → name resolution) → repoint edge to RESOLVED uuids → merge attributes/summary/labels onto resolved nodes → duplicate-uuid guard → run the standard two-search + `resolve_extracted_edge` pipeline against a synthetic episode (`valid_at=edge.valid_at or utc_now()`, empty content, no custom types ⇒ typed-attribute extraction skipped) → embed resolved+invalidated → bulk write `[resolved_edge] + invalidated_edges`.
**Invariant:** (1) merge semantics are per-field and asymmetric — attributes dict-update, summary only-if-truthy, labels set-union; a port that wholesale-assigns the incoming node erases existing graph state; (2) an existing edge uuid pointing at DIFFERENT endpoints never overwrites — it becomes a new fact; (3) contradiction handling reuses the identical resolver as extraction (one code path, one prompt contract), not a bespoke "direct write" shortcut.
**Probe:** `.venv/bin/python -m pytest tests/test_add_triplet.py -k "merges_attributes or updates_summary or updates_labels" -q` (DB-backed: `attributes['age'] == 31  # Updated value` while `'city' ... # Preserved`; battery: `grep -c "attributes\['age'\] == 31" tests/test_add_triplet.py` → 2; `grep -c 'Preserved' tests/test_add_triplet.py` → 3). Anchored at repo root. MCP-side shape guard: `mcp_server/tests/test_core_parity.py::test_triplet_objects_construct :263-277`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "add_triplet NodeNotFoundError resolve_extracted_nodes uuid4 overwrite", limit: 6, fields: ["signature", "name", "file"] });
// rank family: Graphiti.add_triplet :1645-1763 + tests/test_add_triplet.py trio
```

## Verdict
Adopt resolve-or-create endpoints, the three merge rules, and the collision-mints-new-uuid guard for any direct-write API layered on an extracted memory graph; adapt the embedding pre-generation to your model client; omit the synthetic-episode trick if your resolver takes nullable episodes. DB-backed tests need a live Neo4j/FalkorDB driver (env-gated matrix, tests/helpers_test.py:33-58) — coverage caveat for CI without backends.
