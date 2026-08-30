<!-- capsule-v2 -->
# Bulk dedup — UnionFind canonicalization + combined extraction

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does bulk ingestion dedup many duplicate-pairs into one canonical id per cluster, and extract nodes+edges in a single LLM pass?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/bulk_utils.py` (634 lines): `UnionFind` (:584-603), `compress_uuid_map` (:606-621), `resolve_edge_pointers` (:627-633), `extract_nodes_and_edges_bulk` (:263), `_extract_nodes_and_edges_bulk_combined` (:295) vs `_separate` (:330), `dedupe_nodes_bulk` (:374), `dedupe_edges_bulk` (:489), `add_nodes_and_edges_bulk_tx` (:151); `maintenance/combined_extraction.py`: `extract_nodes_and_edges` (:41).
**Signature:** `compress_uuid_map(duplicate_pairs)` — union all pairs, return `id -> lexicographically-smallest id in its set`; `resolve_edge_pointers(edges, uuid_map)` — remap edge source/target through the map; `UnionFind.union` attaches the lexicographically larger root under the smaller.
**Data Shape:** duplicate pairs from fuzzy/LLM dedup; canonical representative = smallest uuid; edges keep their own identity but get their endpoint pointers rewritten.

### Decisive source
```ts
class UnionFind:
    def find(self, x):                    # path compression
        if self.parent[x] != x: self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return
        if ra < rb: self.parent[rb] = ra  # lexicographically smaller root wins
        else:       self.parent[ra] = rb
def compress_uuid_map(duplicate_pairs):
    uf = UnionFind(all_uuids)
    for a, b in duplicate_pairs: uf.union(a, b)
    return {uuid: uf.find(uuid) for uuid in all_uuids}
def resolve_edge_pointers(edges, uuid_map):
    edge.source_node_uuid = uuid_map.get(edge.source_node_uuid, edge.source_node_uuid)
```

**Flow:** pairwise duplicate decisions (from MinHash/LSH + LLM confirmation) feed `union` → `compress_uuid_map` collapses each duplicate cluster to its canonical (smallest) uuid → nodes merge under the canonical id → `resolve_edge_pointers` rewrites every edge endpoint that pointed at a merged node. Extraction can run combined (one LLM call for nodes+edges via `extract_nodes_and_edges`) or separate per kind, chosen by bulk mode.
**Invariant:** the canonical representative is deterministic (lexicographic min); union-find uses path compression so map building stays near-linear; edge pointers never dangle after compression; combined vs separate extraction is a strategy choice, not a behavior change.
**Probe:** `tests/` bulk tests (transitive duplicates A~B~C collapse to one canonical id; edge endpoints remapped; combined extraction returns both nodes and edges).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "UnionFind compress_uuid_map resolve_edge_pointers dedupe_nodes_bulk combined extraction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt union-find canonicalization for transitive duplicate clusters + pointer rewriting on edges; choose combined vs separate extraction as a cost/quality strategy. Adapt canonical-selection rule to host.
