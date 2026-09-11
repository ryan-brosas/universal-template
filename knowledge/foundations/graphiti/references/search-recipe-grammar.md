<!-- capsule-v2 -->
# Search recipe grammar — per-family method/reranker matrices + SearchResults.merge

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** what is the declarative recipe that drives every search family (edge/node/episode/community), and how are per-family search results merged?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search_config.py` (`EdgeSearchMethod`/`NodeSearchMethod`/`EpisodeSearchMethod`/`CommunitySearchMethod`, `EdgeReranker`/`NodeReranker`/`EpisodeReranker`/`CommunityReranker`, `EdgeSearchConfig`/`NodeSearchConfig`/`EpisodeSearchConfig`/`CommunitySearchConfig`, `SearchConfig`, `SearchResults`); `SearchResults.merge` (:131–160).
**Signature:** `SearchConfig(edge_config=None, node_config=None, episode_config=None, community_config=None, limit=10, reranker_min_score=0)`; `SearchResults.merge(results_list: list[SearchResults]) -> SearchResults`.
**Data Shape:** each family has a `search_methods: list[Enum]` and a `reranker: Enum` (default `rrf`). `sim_min_score`/`mmr_lambda`/`bfs_max_depth` default from `search_utils` (`DEFAULT_MIN_SCORE`, `DEFAULT_MMR_LAMBDA`, `MAX_SEARCH_DEPTH`). `SearchResults` holds parallel lists: `edges` + `edge_reranker_scores`, `nodes` + `node_reranker_scores`, `episodes` + `episode_reranker_scores`, `communities` + `community_reranker_scores`.

### Decisive source
```python
class EdgeSearchMethod(Enum):  cosine_similarity; bm25; bfs
class EpisodeSearchMethod(Enum):  bm25        # episodes have NO vector/cosine path
class CommunityReranker(Enum):  rrf; mmr; cross_encoder   # no node_distance/episode_mentions

class SearchResults(BaseModel):
    @classmethod
    def merge(cls, results_list):
        if not results_list:
            return cls()
        merged = cls()
        for result in results_list:
            merged.edges.extend(result.edges)
            merged.edge_reranker_scores.extend(result.edge_reranker_scores)
            # ... same extend for nodes/episodes/communities + score lists ...
        return merged
```

**Flow:** a caller builds a `SearchConfig` (or per-family `*SearchConfig`) naming which search methods to run and which reranker to apply, then the search engine dispatches each method (cosine/bm25/bfs) and fuses via the reranker; `SearchResults.merge` concatenates results from multiple configs into one aggregate object, keeping each family's items and their reranker scores in lockstep.
**Invariant:** (1) the method/reranker matrices are NOT uniform across families — `EpisodeSearchMethod` has only `bm25` (no cosine/bfs), `EpisodeReranker` has only `rrf`/`cross_encoder`, `CommunityReranker` omits `node_distance`/`episode_mentions`; (2) `merge` is plain concatenation (no dedup, no re-ranking) — it preserves order and score-list parity; (3) each family's items and score list must stay the same length after any operation (parallel-list invariant).
**Probe:** `tests/utils/search/test_search_security.py` (pins search filtering/security behavior driven by these configs); the merge/parallel-list shape is asserted by search integration tests in `tests/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "SearchConfig SearchResults merge EdgeSearchMethod EpisodeReranker reranker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the declarative per-family config grammar (it makes adding a search family a data change, not code) and the parallel-list `SearchResults` shape; adapt the merge to dedup if your pipeline can return overlapping results; omit the specific enum values that don't apply to your store. Complements `search.md` (the runtime recipe) by pinning the config schema and merge contract.
