<!-- capsule-v2 -->
# Graph operations interface — dual watermark, direction-limited edge reads

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** what invariants does the shared graph-mutation/read interface maintain that a porter would get wrong — especially the two saga watermarks and the direction-limited edge queries?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/graph_operations/graph_operations.py:GraphOperationsInterface` (:22–893); `saga_get_episode_contents` (:380–408), `saga_get_previous_episode_uuid` (:362–378), `retrieve_episodes` (:200–226), `edge_get_between_nodes` (:853–873), `edge_get_by_node_uuid` (:875–893), `get_community_clusters` (:746–766), `determine_entity_community` (:786–807), `clear_data` (:731–744).
**Signature:** `async saga_get_episode_contents(driver, saga_uuid, since=None, limit=200) -> list[tuple[str, datetime|None]]`; `async edge_get_between_nodes(_cls, driver, source_node_uuid, target_node_uuid) -> list[EntityEdge]`.
**Data Shape:** a pydantic `BaseModel` interface; every method is `async def` raising `NotImplementedError` — concrete drivers subclass and implement. All params are `Any`-typed to avoid circular imports (docstrings carry the real types). `_cls` is a "kept for parity" positional that callers don't pass.

### Decisive source
```python
# saga_get_episode_contents — the DUAL WATERMARK trap
# since: compared against episode.created_at (INGESTION time) — filters which
#   episodes to summarize. Returns (content, valid_at) pairs in chronological
#   order by valid_at. The returned valid_at is used by the caller to advance
#   saga.last_summarized_episode_valid_at (the TEMPORAL watermark), which is
#   DISTINCT from last_summarized_at (wall-clock, the INGESTION-time filter watermark).
```
```python
# edge_get_between_nodes — DIRECTION-LIMITED
# Returns only edges in the source->target direction. A porter assuming
# undirected lookup would miss reverse-direction edges.
```

**Flow:** the interface groups operations by node/edge type (Entity/Episodic/Community/Saga × save/delete/read/embedding-load) plus saga queries, search helpers (`get_mentioned_nodes`, `get_communities_by_nodes`), and maintenance (`clear_data`, `get_community_clusters`, `remove_communities`, `determine_entity_community`). Concrete drivers implement each method against their dialect.
**Invariant:** (1) the saga summarization uses TWO watermarks — `last_summarized_at` (wall-clock, filters by ingestion time `created_at`) vs `last_summarized_episode_valid_at` (temporal, advanced by the returned `valid_at`); conflating them breaks backfilled episodes with historical reference times; (2) `edge_get_between_nodes` returns only `source->target` direction — the reverse direction is a separate lookup; (3) `retrieve_episodes` filters by `valid_at <= reference_time` (point-in-time) and returns oldest-first; (4) `edge_get_by_node_uuid` returns edges where the node is source OR target (undirected), unlike `edge_get_between_nodes`.
**Probe:** `tests/utils/maintenance/test_edge_operations.py` + `test_node_operations.py` (pin the edge/node read contracts); saga summarization behavior is exercised by orchestrator integration tests in `tests/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "saga_get_episode_contents last_summarized_episode_valid_at edge_get_between_nodes determine_entity_community", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-watermark saga-summarization contract (temporal vs ingestion watermark) and the direction-limited edge-read semantics verbatim — both are high-risk to port wrong; adapt the concrete method bodies to your store; omit the `_cls` parity positional if your interface doesn't need it. This is the shared interface behind the dialect-specific `driver/operations/*` mixins.
