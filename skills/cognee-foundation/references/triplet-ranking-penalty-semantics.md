<!-- capsule-v2 -->
# Triplet ranking — vector distances onto a projected graph, penalties as defaults

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How are per-collection vector hits combined into top-k graph triplets without letting unsearched elements outrank real matches?

## CogneeGraph projection + scoring
**Path/Symbol:** `cognee/modules/graph/cognee_graph/CogneeGraph.py:_calculate_query_top_triplet_importances` (:417-505), `project_graph_from_db` (:232-281), `map_vector_distances_to_graph_nodes` (:338-371); driver `brute_force_triplet_search` (`cognee/modules/retrieval/utils/brute_force_triplet_search.py:225-376`).
**Signature:** `heapq.nsmallest(k, self.edges, key=score)`; score = Σ over (node1, node2, edge) of `(2 - importance_weight) * distance`, feedback/personal blended.
**Data Shape:** Distance default = `triplet_distance_penalty` (6.5). Node/Edge store `vector_distance: list[float]` (one slot per query); edges indexed by `edges_by_distance_key[edge_type_id]` so one EdgeType vector hit updates ALL edges sharing that type text.

### Decisive source
```python
# Only blend REAL cosine distances in [0, 2]. Fallback penalties and out-of-range
# values must remain unchanged so missing components stay ranked below valid matches:
if distance >= self.triplet_distance_penalty or distance < 0.0 or distance > 2.0:
    return distance
normalized_distance = distance / 2.0
blended = (1-infl)*normalized_distance + infl*(1 - normalized_feedback_weight)
return blended * 2.0
# personal layer: RAW decides whether, BLENDED decides what — testing the returned
# value instead would scale fallback penalties like real matches.
if raw >= self.triplet_distance_penalty or raw < 0.0 or raw > 2.0:
    return blended
```

**Flow:** vector search across collections (`Entity_name`, `TextSummary_text`, `EntityType_name`, `DocumentChunk_text`, `DltRow_text`, + appended `EdgeType_relationship_name`; caller lists COPIED because persistent caller lists must not gain the edge collection in place) → project graph (full, ID-filtered w/ empty-fallback-to-full, or nodeset subgraph; neighborhood mode re-scores expansion nodes via ID-filtered vector search so they don't sit at penalty) → map distances per query index → apply personal weights AFTER mapping → nsmallest by summed score.
**Invariant:** (1) Penalty-defaults are the "no information" rank — blending them would let absent evidence compete with matches. (2) Edges whose endpoints weren't projected are SKIPPED with a debug log, never raised (#2897: partial filtering is the norm on real graphs). (3) Batch vs single mode differ only in list nesting; `_normalize_query_distance_lists` enforces length match. (4) `CollectionNotFoundError` ⇒ empty results, never an error.
**Probe:** `cognee/tests/unit/modules/graph/cognee_graph_test.py::test_calculate_top_triplet_importances`, `::test_calculate_top_triplet_importances_default_distances`, `::test_calculate_top_triplet_importances_multi_query`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "calculate_top_triplet_importances triplet_distance_penalty feedback blend", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt penalty-as-default distance semantics and eligibility-guarded blending (raw-vs-blended distinction); adapt collection names/weights to your schema; omit the personalization layer when you have no preference store.
