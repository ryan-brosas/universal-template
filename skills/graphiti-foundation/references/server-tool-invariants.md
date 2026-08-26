<!-- capsule-v2 -->
# Server tool-surface invariants — queue-first writes, recipe selection, safe deletes

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** what ordering and selection rules must an MCP/HTTP wrapper around a memory engine preserve so callers never get silent background failures or wrong-ranked results?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/graphiti_mcp_server.py`: `add_memory` (:355), `search_nodes` (:491), `delete_episode` (:674), `summarize_saga` (:800), `add_triplet` (:906), `get_status` (:1060); semaphore tuning table (:67-94).
**Signature:** tools return typed unions (`SuccessResponse | ErrorResponse`) instead of raising; `add_memory(...)` returns immediately after enqueueing.
**Data Shape:** every list-taking param accepts scalar-or-list via `coerce_group_ids`; effective group falls back to `[config.graphiti.group_id]` when omitted.

### Decisive source
```python
# add_memory — parse BEFORE enqueue: malformed timestamp fails fast to the caller,
# it does not rot in the background worker's logs:
try:
    parsed_reference_time = parse_reference_time(reference_time)
except ValueError as e:
    return ErrorResponse(error=f'Invalid reference_time: {e}')
...
# search_nodes — center-node ranking only exists inside ONE recipe; selecting RRF
# with a center_node_uuid would silently ignore it:
node_config = (NODE_HYBRID_SEARCH_NODE_DISTANCE if center_node_uuid
               else NODE_HYBRID_SEARCH_RRF)
...
# delete_episode — cascade delete, NOT EpisodicNode.delete (which orphans the
# entities/facts the episode solely created):
await client.remove_episode(uuid)
```

**Flow:** write path = validate → enqueue per group_id → 202-style ack (`'queued for processing'`); read paths resolve effective group ids, pick the search recipe matching the requested features, strip embeddings in formatters (`to_node_result` filters any attribute key containing 'embedding'); saga summarization resolves saga NAME → uuid within the group first (`SagaNode.get_by_group_ids`, name match) because core keys sagas by (name, group_id) but summarize needs the uuid; unknown `source` strings degrade to `EpisodeType.text` with a warning rather than erroring.
**Invariant:** four rules that prevent silent misbehavior in any port: fail fast on caller-supplied parseables BEFORE async handoff; feature-requested capabilities must select the code path that implements them (recipe ↔ feature coupling); destructive ops choose the cascading API over the raw one; health/status probes exercise the real dependency (`MATCH (n) RETURN count(n)`) not a static string. Concurrency is capped by a documented SEMAPHORE_LIMIT env with provider-rate-limit tuning guidance (:75-93).
**Probe:** `mcp_server/tests/test_core_parity.py::TestCoreSignatureCompatibility::test_queue_service_kwargs_are_accepted_by_add_episode` + `test_core_exposes_parity_methods` (server kwargs stay signature-compatible with core's `Graphiti.add_episode`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "add_memory search_nodes remove_episode summarize_saga NODE_HYBRID_SEARCH_NODE_DISTANCE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper contract rules (fail-fast validation before queues, recipe-feature coupling, cascade deletes, live-dependency health checks). Adapt response-type shapes to your RPC layer. Omit the FastMCP decorators themselves; the invariants are the portable part.
