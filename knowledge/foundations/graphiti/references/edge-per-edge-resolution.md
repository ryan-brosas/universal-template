<!-- capsule-v2 -->
# Per-edge LLM resolution — exact-fact short circuit, offset index space, expiry ladder

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how does a single extracted edge get resolved against candidates — when is the LLM skipped, how are its integer answers mapped back, and who expires whom?

## Per-edge LLM resolution
**Path/Symbol:** `graphiti_core/utils/maintenance/edge_operations.py`: `resolve_extracted_edge` (:623-847); empty-candidates attribute path (:653-682); verbatim fast path (:684-695); continuous index context + validation (:699-776); stale-attribute clearing (:806-809); new-edge self-expiry (:820-839).
**Signature:** `async resolve_extracted_edge(llm_client, extracted_edge, related_edges, existing_edges, episode, edge_type_candidates=None) -> tuple[EntityEdge, list[EntityEdge], list[EntityEdge]]` → `(resolved_edge, invalidated_edges, duplicate_edges)`.
**Data Shape:** `related_edges` = same-endpoint duplicate candidates; `existing_edges` = broader contradiction candidates; the LLM prompt presents BOTH lists in ONE continuous index space (duplicates at 0..len(related)-1, invalidation shifted by `invalidation_idx_offset`).

### Decisive source
```python
# Fast path: endpoints equal AND fact equal after lowercase/whitespace collapse
# -> reuse WITHOUT any LLM call; only append the episode uuid:
if (edge.source_node_uuid == extracted_edge.source_node_uuid
        and edge.target_node_uuid == extracted_edge.target_node_uuid
        and _normalize_string_exact(edge.fact) == normalized_fact):
    resolved = edge
    if episode is not None and episode.uuid not in resolved.episodes:
        resolved.episodes.append(episode.uuid)
    return resolved, [], []

# Continuous index space: invalidation candidates START where duplicates end
invalidation_idx_offset = len(related_edges)

# Map LLM integers back THROUGH the offset:
for idx in contradicted_facts:
    if 0 <= idx < len(related_edges):
        invalidation_candidates.append(related_edges[idx])
    elif invalidation_idx_offset <= idx <= max_valid_idx:
        invalidation_candidates.append(existing_edges[idx - invalidation_idx_offset])
```

**Flow:** both candidate lists empty → still run typed-attribute extraction + timestamp extraction, return early · verbatim match in `related_edges` → reuse that edge object, append episode uuid, zero LLM calls · otherwise ONE small-model call (`dedupe_edges.resolve_edge`) returns `{duplicate_facts: [int], contradicted_facts: [int]}` → out-of-range indices logged and dropped (`duplicate_facts` valid range 0..len(related)-1; `contradicted_facts` 0..max_valid_idx across the JOINT space) → first duplicate id wins (`for ... break`, :747-749) and resolved becomes THAT existing object · attributes: if an edge-type model matches `resolved_edge.name` merge via `apply_capped_attributes(merge_mode='replace')`, else CLEAR `resolved_edge.attributes = {}` (no matching schema ⇒ no stale attributes survive) · timestamps extracted ONLY for genuinely-new edges (`resolved_edge.uuid == extracted_edge.uuid`, duplicated edges keep theirs, :812) · self-expiry: if any candidate's `valid_at > resolved.valid_at` (candidates pre-sorted by `(valid_at is None, valid_at)`), the NEW edge gets `invalid_at = candidate.valid_at`, `expired_at = now` · finally `resolve_edge_contradictions` expires OLD edges whose valid window overlaps.
**Invariant:** (1) never trust raw LLM integers — every index is range-checked against the exact list it should address, with the offset applied for the second list; (2) duplicate resolution reuses the EXISTING edge object (identity preserved, uuid unchanged) so downstream uuid-equality tests detect "not new"; (3) timestamps are set exactly once per edge lifetime — `_extract_edge_timestamps` returns immediately if either timestamp exists (:587); (4) attributes follow "schema-match or wipe", never silently keep prior-schema keys.
**Probe:** `.venv/bin/python -m pytest tests/utils/maintenance/test_edge_operations.py::test_resolve_extracted_edge_exact_fact_short_circuit tests/utils/maintenance/test_edge_operations.py::test_resolve_extracted_edge_uses_integer_indices_for_duplicates tests/utils/maintenance/test_edge_operations.py::test_resolve_extracted_edge_overcap_attribute_preserves_prior -q`. Anchored at repo root. Battery: `grep -c 'resolved_edge.episodes.append' graphiti_core/utils/maintenance/edge_operations.py` → 1; `grep -c 'invalidation_idx_offset = len(related_edges)' graphiti_core/utils/maintenance/edge_operations.py` → 1; `grep -c 'if resolved_edge.uuid == extracted_edge.uuid' graphiti_core/utils/maintenance/edge_operations.py` → 2; `grep -c 'generate_response.assert_not_called' tests/utils/maintenance/test_edge_operations.py` → 1; `grep -c 'assert len(duplicates) == 2' tests/utils/maintenance/test_edge_operations.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "duplicate_facts contradicted_facts EdgeDuplicate resolve_extracted_edge", limit: 8, fields: ["signature", "name", "file"] });
// rank-1: edge_operations.resolve_extracted_edge :623-847 + its three direct tests
```

## Verdict
Adopt the verbatim fast path, the continuous-index prompt mapping with range validation, identity-preserving duplicate reuse, and the two-sided expiry ladder (new edge self-expires vs older facts; older contradicting edges expire via arithmetic windows); adapt prompt shape/model size to host LLM stack; omit the specific prompt library. Direct tests run in default CI (mock LLM, no DB).
