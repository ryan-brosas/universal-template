<!-- capsule-v2 -->
# Dataset deletion plane — graph+vector+relational teardown with slug protection

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you delete a dataset's graph content without destroying nodes shared with other datasets?

## delete_from_graph_and_vector + delete methods family
**Path/Symbol:** `cognee/modules/graph/methods/delete_from_graph_and_vector.py` (:1-175), `delete_dataset_nodes_and_edges.py`, `delete_data_nodes_and_edges.py` (:1-127), `get_shared_slugs_losing_dataset_anchor.py` (:1-74), legacy bridge `legacy_delete.py` (:1-123) + `has_nodes_in_legacy_ledger.py`.
**Signature:** `async delete_from_graph_and_vector(nodes, edges, is_legacy_node, is_legacy_edge)`.
**Data Shape:** Slug = shared human-readable identity across datasets; deletion eligibility requires the slug to lose its LAST dataset anchor.

### Decisive source
```python
# A node/edge is deleted from graph+vector only when no OTHER row keeps the slug:
# get_shared_slugs_losing_dataset_anchor — slugs still anchored in another
# dataset survive; only unshared slugs reach the graph/vector delete.
```

**Flow:** select dataset-scoped rows → partition into deletable vs still-anchored-by-other-datasets → detect legacy-ledger rows (pre-provenance format) and route them through the legacy bridge → graph delete → vector delete by id → relational row cleanup; the SAME lock registry (`cognee/infrastructure/locks`) serializes deletes against running pipelines on the dataset.
**Invariant:** (1) Cross-dataset sharing is judged at SLUG granularity, not id — two datasets legitimately hold distinct rows for the same real-world entity, and deleting one dataset must not erase the entity for the other. (2) Legacy-format rows are deleted through their own path rather than crashing the modern one (backward compatibility is a routing concern). (3) Deletes take the per-dataset lock like pipelines do — mutation serialization is symmetric.
**Probe:** `cognee/tests/unit/modules/graph/test_graph_methods.py`; `test_delete_detag_nodeset.py`; `cognee/tests/test_delete_all_with_mixed_permissions.py::test_delete_all_permission_error_handling`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "delete_from_graph_and_vector shared slugs losing dataset anchor legacy", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt slug-anchor protection and legacy-path routing in deletes; adapt slug semantics to your identity scheme; omit permission checks (product layer).
