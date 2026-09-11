<!-- capsule-v2 -->
# tag-feature-pagerank-boost — how do query tags and PageRank enter ranking?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What is the exact formula combining tag cosine, PageRank, and the blended similarity — and where does it NOT apply?

## Rank-feature scoring + retrieval blend
**Path/Symbol:** `_tag_feature_scores` `rag/nlp/search.py:362-387`; `_rank_feature_scores` `:389-392`; blend in `rerank*`/`retrieval` (`:486-489`, `:519-523`, `:546-550`); GaussDB divergence `:677-684`; default rank_feature `{PAGERANK_FLD: 10}` at `:595`.
**Signature:** `_tag_feature_scores(query_rfea, search_res) -> np.array(float)` (×10.0); `_rank_feature_scores = tags + pageranks`.
**Data Shape:** chunk TAG_FLD parsed via `parse_tag_features(..., allow_json_string=True, allow_python_literal=True)`; score = Σ(q_t·s_t)/ (√Σs²·√Σq² over non-PAGERANK terms only) × 10.

### Decisive source
```python
def _rank_feature_scores(self, query_rfea, search_res):
    ## For rank feature(tag_fea) scores.
    pageranks = np.array([search_res.field[chunk_id].get(PAGERANK_FLD, 0) for chunk_id in search_res.ids], dtype=float)
    return self._tag_feature_scores(query_rfea, search_res) + pageranks
...
sim = tkweight * tksim + vtweight * vtsim + rank_fea        # rerank_with_knn :489
return sim + rank_fea, tksim, vtsim                          # local rerank :523
# GaussDB: server already fused + applied PageRank in SQL — add ONLY tags locally
sim = sql_scores + self._tag_feature_scores(rank_feature, sres)   # :682
```

**Flow:** empty/zero query features → zero vector (no boost); per chunk: cosine between query tag weights and stored TAG_FLD weights scaled ×10, plus raw PAGERANK_FLD value; added AFTER the tk/vt blend so it can reorder but not rescale similarities. Infinity path skips local rank features entirely (`_score` already fused server-side, comment "Don't need rerank here since Infinity normalizes each way score before fusion" :661-666). Threshold note: `post_threshold` drops to 0.0 when `vector_similarity_weight <= 0` (:708-709) because a term-only score never clears a vector-calibrated threshold.
**Invariant:** PAGERANK excluded from BOTH normalization denominators (query denor skips it; it's added unnormalized) — folding it into the cosine would let one high-rank doc dominate every result page. GaussDB must not re-add pagerank (its own test pins this: test_tc_ret_704_..._does_not_add_pagerank_twice).
**Probe:** `grep -n 'def _tag_feature_scores\|def _rank_feature_scores' rag/nlp/search.py` → :362/:389; `sed -n '708,709p' rag/nlp/search.py | grep -c 'post_threshold'` → 1; gaussdb no-double-add pinned by executed suite `test_gaussdb_retrieval.py` 9/9 GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "_tag_feature_scores pagerank rank feature", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the add-after-blend ordering and the pagerank-outside-cosine rule; adapt the ×10 scale and default {pagerank:10}; omit local tag scoring for engines that fuse server-side (keep the GaussDB double-add trap as porting warning).
