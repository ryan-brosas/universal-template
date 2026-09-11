<!-- capsule-v2 -->
# Episode deletion cascade — first-episode ownership, single-mention node GC, delete order

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when one episode is removed from a shared memory graph, which edges and nodes may be deleted — and in what order?

## Episode deletion cascade
**Path/Symbol:** `graphiti_core/graphiti.py`: `remove_episode` (:1765-1793); first-episode edge ownership test (:1772-1776); per-node MENTIONS count (:1778-1788); two-phase delete + episode last (:1790-1793).
**Signature:** `async remove_episode(self, episode_uuid: str) -> None`.
**Data Shape:** relies on the same `EpisodicNode.entity_edges` backpointer list as the provenance read; node candidacy requires a live MENTIONS count query, not a cached field.

### Decisive source
```python
# OWNERSHIP: an episode may delete an edge only if it is the FIRST episode
# in the edge's episodes list (i.e. the episode that CREATED it):
for edge in edges:
    if edge.episodes and edge.episodes[0] == episode.uuid:
        edges_to_delete.append(edge)

# NODE GC: delete a mentioned node only when this is its LAST mentioning
# episode (count == 1 means only THIS episode still mentions it):
'MATCH (e:Episodic)-[:MENTIONS]->(n:Entity {uuid: $uuid}) RETURN count(*) AS episode_count'
...
if record['episode_count'] == 1:
    nodes_to_delete.append(node)

# ORDER matters: edges -> nodes -> the episode row itself.
await Edge.delete_by_uuids(self.driver, [edge.uuid for edge in edges_to_delete])
await Node.delete_by_uuids(self.driver, [node.uuid for node in nodes_to_delete])
await episode.delete(self.driver)
```

**Flow:** load episode → resolve its backpointer edge uuids → keep edges whose `episodes[0]` is this episode (later episodes merely reference the fact) → for every MENTIONS'd node run the count query and keep those with exactly one mention → delete edges, then orphaned nodes, then the episode.
**Invariant:** (1) creation-ownership (`episodes[0]`) prevents later episodes that re-stated a fact from destroying it; (2) last-mention GC prevents deleting entities other episodes still reference; both tests are REQUIRED — either alone over-deletes shared structure; (3) deletes are ordered children-first so no dangling references outlive their targets mid-cascade.
**Probe:** `.venv/bin/python -m pytest tests/test_graphiti_mock.py::test_remove_episode -q` (DB-backed round trip: after remove, `assert node_count == 0` / `edge_count == 0`; battery: `grep -c 'assert node_count == 0' tests/test_graphiti_mock.py` → 2; `grep -c 'if edge.episodes and edge.episodes\[0\] == episode.uuid:' graphiti_core/graphiti.py` → 1). Anchored at repo root. Requires a live driver from the env-gated matrix (tests/helpers_test.py:33-58); skipped/disabled drivers ⇒ coverage caveat rather than silent pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "remove_episode episode_count MENTIONS delete_by_uuids", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: Graphiti.remove_episode :1765-1793 (+ mock round-trip :333-450)
```

## Verdict
Adopt the two-guard cascade (creation ownership + last-mention GC + child-first order) for any episodic memory store; adapt the count query to your backend's aggregation; omit the IoC indirection if single-driver. DB-backed test coverage caveat stated above.
