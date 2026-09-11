<!-- capsule-v2 -->
# Hybrid multi-query fusion — how do lexical and vector scores combine, and how do multiple queries fold into one ranking?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What is the exact score arithmetic for hybrid retrieval with query expansion, including the defaults for unmatched snippets?

## multi_get_top_k_snippets: (lex + 2·vector)/3 fusion then 1/2^j RRF-style fold
**Path/Symbol:** `sweepai/utils/ticket_utils.py:multi_get_top_k_snippets` (:137–202) and the multi-query branch of `multi_prep_snippets` (:311–327); `VECTOR_SEARCH_WEIGHT=2`, `NUM_SNIPPETS_TO_RERANK=100` (:134–135).
**Signature:** `multi_get_top_k_snippets(cloned_repo, queries: list[str], k=15, ...) -> Iterator[tuple[str, list[Snippet], list[Snippet], dict]]` (`@streamable`).
**Data Shape:** Per query: `content_to_lexical_score: dict[denotation, float]`; vector scores arrive as `files_to_scores_list[i].get(snippet.denotation)` dicts; `ranked_snippets_list` = per-query top-k lists.

### Decisive source
```python
vector_score = files_to_scores_list[i].get(snippet.denotation, 0.04)
snippet_score = 0.02
if snippet.denotation in content_to_lexical_score_list[i]:
    snippet_score = (content_to_lexical_score_list[i][snippet.denotation] + (
        vector_score * VECTOR_SEARCH_WEIGHT
    )) / (VECTOR_SEARCH_WEIGHT + 1)
else:
    snippet_score = snippet_score * vector_score      # 0.02 · vector
...
# multi-query fold (multi_prep_snippets :318-322):
content_to_lexical_score[snippet.denotation] += \
    content_to_lexical_score_list[i][snippet.denotation] * (1 / 2 ** (rank_fusion_offset + j))
```

**Flow:** build lexical index once over the cached repo tree (progress yielded per stage) → run per-query lexical search → compute vector scores for all queries in one batched pass → fuse per query as `(lex + 2·vec)/3` (weight tuned on an internal 50-case benchmark) → sort each query's candidates and keep top-k where k is inflated to `k·3` when multi-query is active → fold all queries by adding each snippet's fused score scaled by its position rank `1/2^j` → truncate to k. Digit penalty applies after every fusion write.
**Invariant:** Snippets missing from a query's lexical hits are NOT dropped — they get the `0.02·vector` floor so vector-only matches survive; lexical-present snippets default vector to `0.04`. The positional decay means query #0 (the user's original, always first) dominates: a top-1 hit on the main query outranks anything from expansion queries two orders down.
**Probe:** No offline unit test (needs repo cache + embedding keys — coverage caveat). Deterministic probes at pin: `grep -c 'VECTOR_SEARCH_WEIGHT' sweepai/utils/ticket_utils.py` → 3; `grep -n 'k \* 3' sweepai/utils/ticket_utils.py` → line 314.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "top k snippets lexical vector search scores ranked", limit: 10 });
// executed at pin: multi_get_top_k_snippets ticket_utils.py 137-202;
// get_top_k_snippets single-query adapter :204-219; get_pointwise_reranked_snippet_scores :221-288
```

## Verdict
Adopt the weighted-average hybrid with explicit floors for one-sided matches and position-decayed multi-query folding that privileges the original query. Adapt the weight constant and floors to your own eval harness (Sweep's comment pins them to a dated benchmark). Omit the streaming yield plumbing if your pipeline has no UI consumer (see streamable capsule).
