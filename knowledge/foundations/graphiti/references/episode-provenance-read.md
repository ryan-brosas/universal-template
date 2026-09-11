<!-- capsule-v2 -->
# Episode provenance read — entity_edges backpointers + MENTIONS join

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** given episode uuids, how do you return exactly the graph elements those episodes produced — and what does "produced" mean for nodes vs edges?

## Episode provenance read
**Path/Symbol:** `graphiti_core/graphiti.py`: `get_nodes_and_edges_by_episode` (:1631-1643); MCP wrapper `get_episode_entities` (`mcp_server/src/graphiti_mcp_server.py:980-1013`, empty-list guard :997-998).
**Signature:** `async get_nodes_and_edges_by_episode(self, episode_uuids: list[str]) -> SearchResults` — returns ONLY `edges` + `nodes` populated.
**Data Shape:** each `EpisodicNode` carries `entity_edges: list[uuid]` — a write-maintained BACKPOINTER list; node side has no such list, so membership is derived by traversing `MENTIONS` from the episodes.

### Decisive source
```python
# Edges: exact production set = the episode's own backpointer list.
episodes = await EpisodicNode.get_by_uuids(self.driver, episode_uuids)
edges_list = await semaphore_gather(
    *[EntityEdge.get_by_uuids(self.driver, episode.entity_edges) for episode in episodes],
    max_coroutines=self.max_coroutines,
)
edges = [edge for lst in edges_list for edge in lst]

# Nodes: DERIVED via the MENTIONS relationship, not stored on the episode:
nodes = await get_mentioned_nodes(self.driver, episodes)
# search_utils.py:131 get_mentioned_nodes -> IoC interface first
# (driver.graph_operations_interface.get_mentioned_nodes), except NotImplementedError,
# else MATCH (episode:Episodic)-[:MENTIONS]->(n:Entity) WHERE episode.uuid IN $uuids
```

**Flow:** load episodes by uuid → fan out per-episode edge-uuid fetches under the shared semaphore → flatten → derive mentioned nodes via provider-routed MENTIONS query → wrap in `SearchResults(edges=..., nodes=...)`. The MCP tool adds the only validation that matters: an empty uuid list is an error response, not "everything".
**Invariant:** (1) edge provenance is EXACT (resolved-invalidated writes maintain `entity_edges`); node provenance is INTENTIONALLY broader — a node mentioned by the episode appears even if it pre-existed; do not "fix" this into symmetric exactness without breaking consumers like `remove_episode`; (2) dedupe responsibility sits with the caller when episode sets overlap (flatten is not distinct'd for edges; MENTIONS query is DISTINCT for nodes).
**Probe:** anchored at repo root. Battery: `grep -c 'MATCH (e:Episodic)-\[:MENTIONS\]->(n:Entity {uuid: $uuid}) RETURN count(*) AS episode_count' graphiti_core/graphiti.py` → 1 (the per-node inverse query used by remove_episode); `grep -c 'def test_remove_episode' tests/test_graphiti_mock.py` → 1 (DB-backed round-trip pins the delete-side of the same backpointer/MENTIONS contract). Direct-test caveat: no default-CI unit test calls `get_nodes_and_edges_by_episode` itself (DB suites env-gated per tests/helpers_test.py:33-58).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "get_nodes_and_edges_by_episode get_mentioned_nodes entity_edges", limit: 5, fields: ["signature", "name", "file"] });
// rank-1 line-exact :1631-1643
```

## Verdict
Adopt backpointer-exact / traversal-derived asymmetry for provenance reads; adapt storage of `entity_edges` to your graph schema (it must be maintained at every edge resolve+invalidate+delete); omit the IoC fallback ladder if you have a single driver. Coverage caveat stated above.
