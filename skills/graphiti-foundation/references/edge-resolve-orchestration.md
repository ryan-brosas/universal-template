<!-- capsule-v2 -->
# Edge resolution pipeline — candidate fan-out, override merge, continuous LLM index

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** before any LLM dedup call runs, how must an edge-resolution orchestrator assemble duplicate candidates, invalidation candidates, and typed-edge subsets so indices stay consistent?

## Edge resolution pipeline (orchestrator)
**Path/Symbol:** `graphiti_core/utils/maintenance/edge_operations.py`: `resolve_extracted_edges` (:325-535); fast-path intra-batch dedup (:344-358); Redis dedup-cache override merge (:372-390); two-search fan-out (:392-430); missing-node hydration (:436-455); signature-filtered edge types (:457-486).
**Signature:** `async resolve_extracted_edges(clients, extracted_edges, episode, entities, edge_types, edge_type_map, existing_edges_override=None) -> tuple[list[EntityEdge], list[EntityEdge], list[EntityEdge]]`.
**Data Shape:** returns `(resolved_edges, invalidated_edges, new_edges)`; "new" is decided by UUID identity — an edge is new iff `resolved_edge.uuid == extracted_edge.uuid` (:524), i.e. resolution kept the freshly minted object rather than returning a canonical existing one.

### Decisive source
```python
# Intra-batch exact dedup BEFORE embeddings/searches: key = (src_uuid, tgt_uuid,
# lowercase+whitespace-collapsed fact); first occurrence wins.
key = (edge.source_node_uuid, edge.target_node_uuid, _normalize_string_exact(edge.fact))

# Override edges (recent Redis-cache resolutions invisible to graph indexes yet)
# are appended PER PAIR with a seen-uuid set — never globally:
existing_uuids = {e.uuid for e in valid_edges_list[i]}
for oe in overrides:
    if oe.uuid not in existing_uuids:
        valid_edges_list[i].append(oe)
        existing_uuids.add(oe.uuid)

# TWO separate searches per extracted edge: duplicates scoped to the pair's
# valid edges via SearchFilters(edge_uuids=...); invalidation UNFILTERED but
# then minus-duplicates by uuid so a candidate never lands in both lists:
related_uuids = {edge.uuid for edge in related_edges}
deduplicated = [edge for edge in invalidation_result.edges if edge.uuid not in related_uuids]
```

**Flow:** exact-dedup batch → embed extracted edges → parallel `get_between_nodes` per pair → merge `existing_edges_override` per-pair (uuid-set guarded) → parallel duplicate search (`EDGE_HYBRID_SEARCH_RRF`, filter `edge_uuids`) + parallel unfiltered invalidation search → subtract duplicate uuids from invalidation lists → hydrate endpoint nodes missing from `entities` via `EntityNode.get_by_uuids` scoped to the FIRST edge's group_id → build per-edge `edge_types_lst` from source/target label-tuple cross product against `edge_type_map` → parallel `resolve_extracted_edge` → split results into resolved/invalidated/new by uuid comparison → embed resolved+invalidated.
**Invariant:** (1) every zip over per-edge lists uses `strict=True` (4 sites :401/:424/:500/:514) — list lengths must stay aligned or the run crashes instead of mis-attributing candidates; (2) duplicate vs invalidation is exclusive — the uuid subtraction guarantees the LLM never sees one edge under both roles; (3) `_normalize_string_exact` = `re.sub(r'\s+', ' ', s.lower()).strip()` (dedup_helpers.py:39-42) — case/whitespace-insensitive but NOT punctuation-insensitive; (4) group_id for missing-node fetch comes from `extracted_edges[0].group_id`, so callers must not mix groups in one call.
**Probe:** `.venv/bin/python -m pytest tests/utils/maintenance/test_edge_operations.py::test_resolve_extracted_edges_fast_path_deduplication tests/utils/maintenance/test_edge_operations.py::test_resolve_extracted_edges_keeps_unknown_names -q` (fast path collapses identical facts before resolve; unknown-name edges survive with `new_edges == resolved_edges`). Anchored at repo root. Battery: `grep -c 'strict=True' graphiti_core/utils/maintenance/edge_operations.py` → 4; `grep -c 'config=EDGE_HYBRID_SEARCH_RRF' graphiti_core/utils/maintenance/edge_operations.py` → 2; `grep -c 'if oe.uuid not in existing_uuids' graphiti_core/utils/maintenance/edge_operations.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "resolve_extracted_edges semaphore_gather invalidation candidates EDGE_HYBRID_SEARCH_RRF", limit: 8, fields: ["signature", "name", "file"] });
// rank-1: edge_operations.resolve_extracted_edges :325-847 family
```

## Verdict
Adopt the three-phase shape (exact-dedup → pair-scoped duplicate search vs unfiltered invalidation search with uuid subtraction → uuid-identity "is new" decision) and the per-pair override merge; adapt the search recipe and override source to host storage; omit the specific Redis cache if unused (pass `None`). Direct tests run in default CI (mocked driver/LLM, no DB needed).
