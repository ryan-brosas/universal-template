<!-- capsule-v2 -->
# Combined extraction — nodes and edges in one LLM call, attribution derived from edges

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** how does single-call extraction keep node/edge consistency, and who owns episode attribution when the LLM emits entities without per-entity episodes?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/combined_extraction.py`: `extract_nodes_and_edges` (:41); helpers reused from `node_operations.py`: `_build_entity_types_context` (:152), `_collapse_exact_duplicate_extracted_nodes` (:336); prompt `prompts/extract_nodes_and_edges.py`: `CombinedExtraction`.
**Signature:** `extract_nodes_and_edges(clients, episode: EpisodicNode | list[EpisodicNode], previous_episodes: list[EpisodicNode], entity_types=None, excluded_entity_types=None, edge_type_map=None, edge_types=None, custom_extraction_instructions=None) -> tuple[list[EntityNode], list[EntityEdge], dict[str, list[int]]]`.
**Data Shape:** LLM returns `CombinedExtraction` = `{extracted_entities: [{name, entity_type_id}], edges: [{source_entity_name, target_entity_name, relation_type, fact, episode_indices}]}` — edges reference nodes by NAME (0-indexed type ids), not uuid; returned map is node uuid → sorted 0-indexed episode positions.

### Decisive source
```python
# Edges are matched to nodes via NORMALIZED names so case/whitespace drift
# from the LLM doesn't drop edges:
name_to_node = {_normalize_string_exact(n.name): n for n in extracted_nodes}
...
# Node attribution is DERIVED from edges, not extracted:
for edge in extracted_edges:
    for node_uuid in (edge.source_node_uuid, edge.target_node_uuid):
        merged = sorted(set(existing + edge_episode_positions))
        node_episode_index_map[node_uuid] = merged
# Nodes with no connecting edges are dropped — no facts ⇒ not stored.
extracted_nodes = [n for n in extracted_nodes if n.uuid in connected_node_uuids]
```

**Flow:** one LLM call (`prompt_library.extract_nodes_and_edges.extract_message`, response_model=CombinedExtraction) → filter empty names → build EntityNodes with labels `{Entity, typed}` from `entity_type_id` → collapse same-message duplicates (specificity rule: more non-`Entity` labels wins; tie broken by longer name) → resolve each edge's endpoints through the normalized-name map (unresolvable endpoints skipped; empty facts skipped) → ONE batched small-model timestamp call (`extract_timestamps_batch`, count-mismatch warned, per-value parse failures logged not raised) → derive node↔episode indices from final surviving edges and drop orphans.
**Invariant:** a stored node always has ≥1 connecting edge in this mode — orphan dropping is what makes "every entity has at least one fact" true rather than aspirational; edge validity depends on name-map resolution, so normalization of BOTH sides must match exactly; duplicate collapse must merge episode-attribution maps alongside the node lists or provenance is lost.
**Probe:** `tests/utils/maintenance/test_entity_extraction.py::TestExtractNodesSmallInput::test_small_input_single_llm_call` + `test_collapses_exact_duplicate_names_preferring_specific_type`; combined path wired via `bulk_utils.extract_nodes_and_edges_bulk(use_combined_extraction=True)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "extract_nodes_and_edges CombinedExtraction _collapse_exact_duplicate_extracted_nodes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-call extraction with name-referenced edges + derived attribution whenever extraction cost dominates (halves LLM calls vs separate passes). Adapt the specificity rule for duplicate collapse. Omit only if your host requires node-first persistence before edge creation. Caveat: bulk wiring is covered by tests; this module's own attribution flow is verified against source at :280-306.
