<!-- capsule-v2 -->
# Same-name entity disambiguation — graph-scoped ordinal ids, not merged names

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** When an LLM extraction emits two DIFFERENT nodes with the same name (two "Apple": company and fruit), how do you avoid wrongly merging them while keeping true mentions deduplicated?

## _calculate_entity_ids_by_extracted_node_id
**Path/Symbol:** `cognee/modules/graph/utils/expand_with_nodes_and_edges.py:_calculate_entity_ids_by_extracted_node_id` (:65-105), `construct_data_points_and_edges` (:188-211), `attach_new_edges_to_data_points` (:214-229).
**Signature:** `(extracted_graph, data_chunk) -> dict[graph_local_node_id, final Entity UUID]`.
**Data Shape:** Name-based id = `Entity.id_for(node.name)`; collision id = `Entity.id_for(name, data_chunk.id, ordinal)` with `ordinal` 1-based over a deterministic sort.

### Decisive source
```python
for name_based_entity_id, same_name_nodes in nodes_by_name_based_id.items():
    if len(same_name_nodes) == 1:
        entity_ids_by_extracted_node_id[node.id] = name_based_entity_id   # merge across chunks
        continue
    ordered_nodes = sorted(same_name_nodes,
        key=lambda n: (generate_node_name(n.type), generate_node_name(n.description),
                       generate_node_name(n.id)))
    for ordinal, node in enumerate(ordered_nodes, start=1):
        # DISTINCT deterministic ids per same-name node within one chunk:
        entity_ids_by_extracted_node_id[node.id] = Entity.id_for(
            node.name, data_chunk.id, ordinal)
```

**Flow:** dedupe duplicate extracted ids first (`_remove_duplicate_extracted_nodes_by_id` keeps first, warns) → per chunk map every extracted node to its final id → entities cached in `data_points_by_id` keyed by str(id) so cross-chunk mentions reuse ONE Entity/EntityType → chunk linked via `(Edge(relationship_type="contains", edge_text="Document chunk mentions X: desc"), entity)` tuples → edges keyed by frozen `EdgeIdentity(source_id, target_id, relationship_name)` in `edges_by_identity` dict (setdefault ⇒ first description wins), already-stored identities filtered via `find_existing_edge_identities` before attach.
**Invariant:** (1) The name→id mapping is computed BEFORE any Entity is constructed — constructing eagerly would bake the wrong id into the first-seen node. (2) Collision fallback scopes by data_chunk.id so two chunks each mentioning "Apple" twice still produce distinct, RECOMPUTABLE ids; the sort key makes the assignment order-stable regardless of LLM output order. (3) EntityType nodes are shared through the same cache (`EntityType.id_for(extracted_type)`).
**Probe:** `cognee/tests/unit/tasks/graph/test_extract_graph_from_data.py::test_integrate_chunk_graphs_keeps_first_node_for_duplicate_extracted_id`; graph tests `cognee/tests/unit/modules/graph/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "_calculate_entity_ids_by_extracted_node_id duplicate name ordinal chunk-scoped", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-tier identity (name-based default + chunk-scoped ordinal on collision); adapt the sort key fields to your extraction schema; omit the ontology twin (`construct_data_points_and_edges_with_ontology`) when you have no resolver.
