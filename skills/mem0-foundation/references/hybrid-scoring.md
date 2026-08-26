<!-- capsule-v2 -->
# Hybrid search scoring — how do semantic, BM25, and entity signals combine without letting keyword noise rescue a bad match?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how are the three retrieval signals fused into one ranked list, and where does the threshold apply?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/scoring.py`: `get_bm25_params` (:16-40), `normalize_bm25` (:43-54), `ENTITY_BOOST_WEIGHT = 0.5` (:57), `score_and_rank` (:60-139); consumed by `mem0/memory/main.py` `_search_vector_store` (:1628-1731) — semantic over-fetch :1641-1644, BM25 scores :1651-1659.
**Signature:** `score_and_rank(semantic_results, bm25_scores, entity_boosts, threshold, top_k, explain=False)`; `normalize_bm25(raw, midpoint, steepness) = 1/(1+exp(-steepness*(raw-midpoint)))`.
**Data Shape:** `bm25_scores`/`entity_boosts` keyed by str(memory_id); candidates `{id, score, payload}`; combined score clamped to 1.0; optional `score_details` dict when `explain=True`.

### Decisive source
```python
# Threshold gates the semantic score BEFORE combining -- candidates
# below the threshold are excluded even if BM25/entity would boost them.
...
max_possible = 1.0
if has_bm25:
    max_possible += 1.0
if has_entity:
    max_possible += ENTITY_BOOST_WEIGHT   # divisor ADAPTS to active signals

raw_combined = semantic_score + bm25_score + entity_boost
combined = min(raw_combined / max_possible, 1.0)
```

**Flow:** `_search_vector_store` over-fetches semantically at `internal_limit = max(limit*4, 60)` → runs `keyword_search` with the LEMMATIZED query (store returns raw BM25 scores or `None` when unsupported) → normalizes each raw BM25 through a length-adaptive sigmoid (≤3 terms: midpoint 5.0/steepness 0.7 … >15: 12.0/0.5) → computes entity boosts → `score_and_rank`: gate on semantic threshold FIRST, add signals, divide by the adaptive max (1.0 / 2.0 / 2.5 / 1.5 depending on which signal sets are non-empty), clamp, sort desc, cut to top_k. The reranker (if enabled) reorders AFTER this fusion in `search()` (:1500-1505).
**Invariant:** a memory below the similarity threshold can never be rescued into results by BM25/entity boosts; the divisor depends on which signals exist so single-signal searches still fill [0,1]; missing BM25 support degrades silently (keyword_results=None → empty dict); `None` semantic score is treated as 0.0.
**Probe:** `tests/utils/test_scoring.py` (`test_threshold_gates_on_semantic` :89, `test_adaptive_divisor_semantic_only` :104, `test_adaptive_divisor_semantic_plus_entity` :110, `test_score_clamped_to_1` :129, `test_explain_includes_score_details` :136).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "score_and_rank bm25 sigmoid normalize entity boost hybrid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the additive-with-adaptive-divisor formula and the threshold-gates-semantic-first rule verbatim — both directions of getting it wrong (rescuing low-semantic hits, fixed divisors distorting single-signal scores) are real bugs; adapt the sigmoid table to your corpus; omit the hosted platform's scoring.
