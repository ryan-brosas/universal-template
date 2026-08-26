<!-- capsule-v2 -->
# Search rerankers — RRF, MMR, node-distance, episode-mentions

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do multiple ranked result lists get fused and diversified so the best facts surface first?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search_utils.py` (2,048 lines): `rrf` (:1764-1779), `node_distance_reranker` (:1782-1843), `episode_mentions_reranker` (:1844-1884), `maximal_marginal_relevance` (:1885-1923), `calculate_cosine_similarity` (:71).
**Signature:**
- `rrf(results: list[list[str]], rank_const=1, min_score=0)` — reciprocal rank fusion across N ranked lists.
- `maximal_marginal_relevance(query_vector, candidates, mmr_lambda=DEFAULT_MMR_LAMBDA, min_score=-2.0)` — relevance + diversity reranking.
- `node_distance_reranker(driver, node_uuids, center_node_uuid)` — graph-distance rerank around a center node.
- `episode_mentions_reranker(...)` — rerank by how often an episode mentions the node.
**Data Shape:** all return `(uuids, scores)` tuples filtered by `min_score`; MMR builds a full similarity matrix over L2-normalized candidate vectors.

### Decisive source
```ts
def rrf(results, rank_const=1, min_score=0):
    for result in results:
        for i, uuid in enumerate(result):
            scores[uuid] += 1 / (i + rank_const)   # reciprocal rank fusion

def maximal_marginal_relevance(query_vector, candidates, mmr_lambda, min_score):
    # normalize candidates (L2), build pairwise similarity matrix
    for i, uuid in enumerate(uuids):
        max_sim = np.max(similarity_matrix[i, :])
        mmr = mmr_lambda * np.dot(query_array, candidate_arrays[uuid]) \
            + (mmr_lambda - 1) * max_sim          # relevance minus redundancy
```

**Flow:** each base search produces a ranked list → RRF fuses multiple lists by summing `1/(rank+const)` → MMR reorders balancing query relevance against already-selected similarity (`λ*rel − (1−λ)*redundancy`) → domain rerankers adjust: node_distance (shortest path to center via RELATES_TO edges; Kuzu needs an intermediate hop) and episode_mentions (mention count in episodes).
**Invariant:** every reranker returns `(uuids, scores)` filtered to `min_score`; MMR penalizes near-duplicate results; provider quirks are isolated behind `driver.search_interface` with a Cypher fallback (NotImplementedError → generic path).
**Probe:** `tests/` search tests (RRF fuses two lists by inverse rank; MMR demotes near-duplicates; distance reranker puts 1-hop nodes above 2-hop).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "rrf maximal_marginal_relevance node_distance_reranker episode_mentions_reranker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt RRF for list fusion + MMR for diversity + graph-distance/mention rerankers as domain signals; adapt λ, rank_const, and thresholds to host.
