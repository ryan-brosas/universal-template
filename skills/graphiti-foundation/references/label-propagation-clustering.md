<!-- capsule-v2 -->
# Label-propagation community clustering — weighted, stability-guarded

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how does Graphiti's community-detection cluster entities, and what the stability guard protects a porter from getting wrong?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/operations/graph_utils.py` (`Neighbor`, `label_propagation`); consumed by `graphiti_core/driver/graph_operations/graph_operations.py:get_community_clusters` (:746–766).
**Signature:** `label_propagation(projection: dict[str, list[Neighbor]]) -> list[list[str]]` where `Neighbor = {node_uuid: str, edge_count: int}`.
**Data Shape:** input maps each node UUID to its weighted neighbors (`edge_count` = strength of the connection); output is a list of clusters, each a list of node UUIDs. `edge_count` is the vote weight, so stronger connections pull nodes into the same community.

### Decisive source
```python
def label_propagation(projection):
    community_map = {uuid: i for i, uuid in enumerate(projection.keys())}
    while True:
        no_change = True
        new_community_map = {}
        for uuid, neighbors in projection.items():
            curr_community = community_map[uuid]
            community_candidates = defaultdict(int)
            for neighbor in neighbors:
                community_candidates[community_map[neighbor.node_uuid]] += neighbor.edge_count
            community_lst = [(count, c) for c, count in community_candidates.items()]
            community_lst.sort(reverse=True)
            candidate_rank, community_candidate = community_lst[0] if community_lst else (0, -1)
            if community_candidate != -1 and candidate_rank > 1:
                new_community = community_candidate      # join the strongest neighbor community
            else:
                new_community = max(community_candidate, curr_community)  # stay put
            new_community_map[uuid] = new_community
            if new_community != curr_community:
                no_change = False
        if no_change:
            break
        community_map = new_community_map
    # group uuids by community id -> list of clusters
```

**Flow:** seed each node as its own community → iteratively, for each node, tally neighbor communities weighted by `edge_count`, pick the strongest candidate → join it ONLY if its weighted rank `> 1` (a single weak edge does not pull a node out of its current community), else stay in the current community (`max(candidate, curr)`) → repeat until a full pass changes nothing → group UUIDs by final community id.
**Invariant:** (1) votes are weighted by `edge_count`, not counted — a strong edge outweighs many weak ones; (2) the `candidate_rank > 1` guard prevents a node from being pulled into a new community by a single weak connection — without it, low-weight noise edges would fragment clusters; (3) `max(community_candidate, curr_community)` keeps the node in its current community when no strong candidate exists (the id comparison is a deterministic tiebreak, not a semantic choice).
**Probe:** `tests/utils/maintenance/test_remove_communities.py` + community-detection tests in `tests/` (pin cluster membership behavior); the `get_community_clusters` interface in `graph_operations.py` calls this internally.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "label_propagation Neighbor get_community_clusters community detection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the weighted label-propagation with the `candidate_rank > 1` stability guard (it is the invariant that keeps clusters coherent); adapt the tiebreak (`max(community_candidate, curr_community)`) to a stable ordering of your choosing; omit if you use a different clustering algorithm. This is the concrete algorithm behind the `community-detection.md` capsule's clustering step.
