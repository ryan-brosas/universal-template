<!-- capsule-v2 -->
# Hybrid entity/fact lanes — 1-hop bullets and EdgeType facts with budget hand-off

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does the entity lane render per-entity edge bullets from a flat neighborhood, and how do standalone "facts" reuse EdgeType vector hits without duplicating what bullets already say?

## build_entities + select_facts_for_entities
**Path/Symbol:** `cognee/modules/retrieval/hybrid/entities.py:build_entities` (:41-77), `_partition_neighborhood` (:80-105), `_edge_sort_key` (:243-250); `hybrid/facts.py:resolve_facts_top_k` (:37-51), `select_facts_for_entities` (:54-75), `connection_edge_type_id` (:13-25).
**Signature:** `build_entities(graph_engine, entity_hits, max_edges_per_entity, edge_ranks, node_name, node_name_filter_operator) -> (entities, reachable_edge_type_ids)`; `EdgeType.id_for(retrieval_text)` mirrors `index_graph_edges._get_edge_text` (top-level edge_text → nested properties.edge_text → relationship_name).
**Data Shape:** Neighborhood rows are `(id, props)` / `(src, tgt, rel_name, props)`; connection triple = `(source, {relationship_name, properties}, target)`; bullet = `{text, source, target, source_id, relationship, target_id, edge_type_id, edge_object_id}`.

### Decisive source
```python
def _partition_neighborhood(entity_ids, nodes, edges):
    # rebuild per-entity triples; drops neighbor-to-neighbor edges
    if source_id in connections: connections[source_id].append(triple)
    if target_id in connections and target_id != source_id:
        connections[target_id].append(triple)

def _edge_sort_key(edge, edge_ranks):
    if _is_type_edge(edge):        return (0, 0)   # pinned is-a first
    rank = edge_ranks.get(edge.get("edge_type_id"))
    if rank is None:               return (2, 0)   # legacy graph order last
    return (1, rank)               # query-ranked middle

def resolve_facts_top_k(entities, *, node_scoped, facts_top_k, entity_edge_budget):
    if entities or node_scoped: return facts_top_k
    return entity_edge_budget   # empty unscoped entity lane spends its edge budget on facts
```

**Flow:** Entity_name hits (search failures degrade to []) → one `get_neighborhood(ids, depth=1)` → partition into per-entity triples (both endpoints register except self-loops) → node-set scoping keeps `is a` type edges unconditionally (EntityType nodes usually lack belongs_to_set) → bullets deduped by (source_id, rel, target_id) then text, sorted by the three-tier key, capped at max_edges_per_entity. Facts lane: EdgeType hits minus ids already shown as bullets, ≥3 words, contains-prefix rewritten to "Name: description".
**Invariant:** (1) Scoped fact selection keeps ONLY hits whose EdgeType id is REACHABLE from a scoped entity — unscoped EdgeType hits cannot leak in where nothing pins them. (2) `connection_edge_type_id` MUST mirror the indexer's text derivation or ranks/reachability silently mismatch. (3) Every graph/vector failure path degrades to fewer results with a warning — never raises.
**Probe:** `cognee/tests/unit/modules/retrieval/hybrid/test_entities_scope.py`; `hybrid_facts_test.py::test_resolve_facts_top_k_uses_entity_budget_when_unscoped_and_empty`, `::test_select_facts_for_entities_keeps_reachable_hits_when_scoped`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "select_facts resolve_facts_top_k build_entities partition_neighborhood", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flat-neighborhood partitioning + tiered bullet ordering + budget hand-off between lanes + mirrored-id reachability filter; adapt the is-a special case and fact word floor to your ontology vocabulary.
