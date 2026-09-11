<!-- capsule-v2 -->
# Harness-only derivation lineage — how do you record "this code produced that output" so the LLM can never assert it?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Why is lineage captured by a harness hook instead of exposed as a tool, and how do version-pinned DERIVED_FROM edges compose with multi-runs of the same code?

## Edges written by POST_TOOL_USE, never by model call; history kept, latest wins
**Path/Symbol:** `backend/python/app/services/artifact_registry/lineage.py:LineageTracker.record_derivation/get_lineage_for_output/get_outputs_for_code` (L157–226); producer cited in-module: `sandbox_bridge.py`'s POST_TOOL_USE hook.
**Signature:** `record_derivation(*, output_artifact_id, code_artifact_id, code_version: int, output_version: int) -> None`; `get_lineage_for_output(output_artifact_id) -> ArtifactLineage | None`; `get_outputs_for_code(code_artifact_id) -> list[ArtifactLineage]`.
**Data Shape:** Edge over the generic `recordRelations` collection: `{from_id (output), from_collection: records, to_id (code), to_collection: records, relationshipType: "DERIVED_FROM", sourceVersion: code_version, derivedVersion: output_version, createdAtTimestamp, updatedAtTimestamp}`.

### Decisive source
```python
# Module docstring, the load-bearing design line:
# "There is deliberately NO public method that takes lineage asserted by a
#  caller-supplied arbitrary pair WITHOUT VERSION NUMBERS PINNED BY THE
#  HARNESS ITSELF — lineage is an observable fact of 'this code run produced
#  these files', captured by sandbox_bridge.py's POST_TOOL_USE hook, NEVER an
#  LLM tool."

# Idempotency is deliberately ABSENT per (output, code) pair:
# every run_code execution against the same code artifact creates a NEW edge
# carrying THAT run's specific versions, preserving which code version made
# which output version — reads collapse via max(createdAtTimestamp).

async def get_lineage_for_output(output_id):
    edges = await graph.get_edges_from_node(f"{_RECORDS}/{output_id}", _RELATIONS)
    derived = [e for e in edges if e.get("relationshipType") == "DERIVED_FROM"]
    if not derived: return None
    latest = max(derived, key=lambda e: e.get("createdAtTimestamp") or 0)
    return ArtifactLineage(..., code_version=int(latest.get("sourceVersion") or 1), ...)
```
Backend-agnostic by construction: only `batch_create_edges` / `get_edges_from_node` / `get_edges_to_node` (generic IGraphDBProvider methods) are used — works unchanged on ArangoDB and Neo4j (`relationshipType` property carries the value exactly like every other RecordRelations entry). Write failure logs-and-returns (never raises): lineage enrichment must not fail a tool result that already succeeded.

**Flow:** sandbox bridge's POST_TOOL_USE fires after each run_code → harness pins the actual code-artifact version + output version it just produced → writes one versioned DERIVED_FROM edge → later reads: output→producing-code (+versions, most recent wins), or code→every output ever derived at any version ("what did this code produce?"). The registry folds lineage onto read metadata in `_with_lineage`, so every resolve/list response carries `derived_from_code_artifact_id`/`_version` when present.
**Invariant:** (1) No LLM-facing write surface exists — asserted lineage would be unfalsifiable; only harness-observed versions are recorded. (2) Non-idempotent append + latest-wins read preserves full run history while keeping answers single-valued. (3) Missing timestamps sort as 0 (`or 0`) so legacy/partial edges can't crash reads. (4) Version ints coerce with `or 1` fallback. (5) Generic-interface-only graph access keeps Arango/Neo4j parity (same discipline as the graph skill store).
**Probe:** `tests/unit/services/artifact_registry/test_lineage.py` (102L): writes_derived_from_edge_with_versions :15; **logs_but_does_not_raise_when_edge_write_fails** :31; returns_none_when_no_lineage :48; most_recent_edge_wins_when_derived_multiple_times :53; ignores_non_derived_from_edges :74; every_output_for_any_version :85; empty_when_no_outputs :99.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "LineageTracker record_derivation get_lineage_for_output DERIVED_FROM" --detail ids
```

## Verdict
Adopt harness-hook-only lineage capture with version-pinned non-idempotent edges, latest-wins reads, log-don't-raise failure posture, and generic-edge-collection portability. Adapt edge collection names to the host graph schema. Omit PipesHub's specific sandbox_bridge wiring.
