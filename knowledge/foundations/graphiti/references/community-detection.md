<!-- capsule-v2 -->
# Community detection — label propagation clustering

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does a knowledge graph cluster entities into communities (for summarization) without a graph library?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/community_operations.py` (367 lines): `label_propagation` (:93-138), `get_community_clusters` (:30), `build_community` (:174), `build_communities` (:216), `determine_entity_community` (:274), `update_community` (:340), `summarize_pair` (:141).
**Signature:** `label_propagation(projection)` — each node starts in its own community; each takes on the plurality community of its neighbors (ties broken by largest community); repeats until no change.
**Data Shape:** `projection: dict[str, list[Neighbor]]` (node_uuid → weighted neighbors); returns `list[list[str]]` clusters; `Neighbor` carries `edge_count` weight.

### Decisive source
```ts
def label_propagation(projection):
    community_map = {uuid: i for i, uuid in enumerate(projection.keys())}
    while True:
        no_change = True
        for uuid, neighbors in projection.items():
            # each node takes the plurality community of its neighbors,
            # weighted by edge_count; ties broken by largest community
            community_candidates[community_map[neighbor.node_uuid]] += neighbor.edge_count
            ...
        if no_change: break
    return clusters  # group uuids by final community
```

**Flow:** each node starts in its own community → iteratively each node adopts the plurality community of its neighbors (weighted by edge count, ties → largest) → repeat until stable → group nodes into clusters. Communities are then summarized (`summarize_pair`/`generate_summary_description`) and built/updated.
**Invariant:** label propagation converges (no change → stop); ties broken deterministically (largest community); clusters feed community summarization.
**Probe:** `tests/` community tests (label propagation clusters connected nodes; ties broken; build_community summarizes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "label_propagation community clusters summarize_pair build_community", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the label-propagation community detection (plurality-of-neighbors, weighted, tie-break by largest) and community summarization; adapt the neighbor weighting and summary prompts to host.
