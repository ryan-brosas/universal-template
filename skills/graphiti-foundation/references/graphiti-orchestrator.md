<!-- capsule-v2 -->
# Graphiti orchestrator — add_episode, bulk, and saga summarization

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does the Graphiti main class ingest an episode, build the graph, and summarize a saga?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/graphiti.py`: `Graphiti` (:137), `add_episode` (:980), `add_episode_bulk` (:1230), `summarize_saga` (:438), `_process_episode_data` (:680), `_extract_and_resolve_nodes` (:604), `_extract_and_resolve_edges` (:631), `_get_or_create_saga` (:346), `build_indices_and_constraints` (:570), `close` (:314).
**Signature:** `add_episode(episode_data, ...)` — extracts nodes/edges from an episode, resolves + dedups them, links to a saga, builds indices; `summarize_saga(saga_id)` — rolls up a saga into a `SagaNode`.
**Data Shape:** `EpisodeData` input; `AddEpisodeResults`/`AddBulkEpisodeResults`/`AddTripletResults` outputs; saga via `_get_or_create_saga`; token tracking via `token_tracker`.

### Decisive source
```ts
class Graphiti:
    async def add_episode(self, episode_data, ...):
        # _get_or_create_saga -> _process_episode_data ->
        #   _extract_and_resolve_nodes + _extract_and_resolve_edges
        # build_indices_and_constraints
    async def summarize_saga(self, saga_id) -> SagaNode:
        # roll up a saga into a summary node
```

**Flow:** `add_episode` gets/creates the saga, processes the episode data (extract + resolve nodes/edges), builds indices/constraints, and returns results. `add_episode_bulk` does the same in batch. `summarize_saga` collapses a saga's episodes into a `SagaNode`. Provider types detected from client class names (`_get_provider_type`).
**Invariant:** every episode is linked to a saga; nodes/edges are extracted + resolved (deduped) before storage; indices/constraints built after ingestion.
**Probe:** `tests/` graphiti tests (add_episode creates the graph; bulk add; summarize_saga collapses the saga; close cleans up).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "Graphiti add_episode summarize_saga saga extract resolve indices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the episode-ingestion orchestrator (get/create saga → extract+resolve nodes/edges → build indices) and saga summarization; adapt the provider clients and saga model to host.
