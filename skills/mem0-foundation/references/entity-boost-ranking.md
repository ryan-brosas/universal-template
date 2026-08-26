<!-- capsule-v2 -->
# Entity boost ranking — how do query entities promote their linked memories without popular entities swamping results?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how are entities extracted from a search query converted into per-memory score boosts, and what keeps a widely-linked entity from dominating?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_compute_entity_boosts` (:1733-1813, sync ThreadPoolExecutor max_workers=4) / `_compute_entity_boosts_async` (:3390-3462); `extract_entities` from `mem0/utils/entity_extraction.py` :751.
**Signature:** `_compute_entity_boosts(query_entities, filters) -> Dict[str, float]` mapping memory_id → MAX boost in [0, 0.5].
**Data Shape:** `query_entities`: list of `(entity_type, entity_text)` tuples; matched entity payloads carry `linked_memory_ids: [memory_id]`; boost formula inputs: match similarity ∈ [0.5, 1], `ENTITY_BOOST_WEIGHT = 0.5`, `memory_count_weight = 1/(1 + 0.001*(n-1)²)`.

### Decisive source
```python
# Deduplicate entities (max 8)
for entity_type, entity_text in query_entities[:8]:   # hard cap at 8 entities
...
similarity = match.score
if similarity < 0.5:            # match threshold, NOT the dedup 0.95
    continue
num_linked = max(len(linked_memory_ids), 1)
memory_count_weight = 1.0 / (1.0 + 0.001 * ((num_linked - 1) ** 2))  # quadratic popularity damping
boost = similarity * ENTITY_BOOST_WEIGHT * memory_count_weight
for memory_id in linked_memory_ids:
    memory_boosts[memory_key] = max(memory_boosts.get(memory_key, 0.0), boost)  # MAX, never SUM
```

**Flow:** extract entities from the raw (unlemmatized) query → dedupe by normalized text capped at 8 → batch-embed → fan out entity-store searches (`top_k=500`) across a 4-worker thread pool (async twin uses `asyncio.to_thread`) → for each match ≥ 0.5 similarity: compute the damped boost and take the running MAX per linked memory → return the boost map to `score_and_rank`.
**Invariant:** boosts are MAX-aggregated per memory (an entity mentioned by many memories of one result never stacks); the quadratic `memory_count_weight` makes an entity linked by N memories contribute ~1/(1+0.001(N-1)²) — near-full weight at small N, heavily damped for hub entities; entity-store failures degrade to zero boosts (warning only), never fail the search; embed-batch length mismatch aborts boosting entirely rather than misaligning vectors.
**Probe:** `tests/utils/test_entity_extraction.py`; scoring-side consumption pinned in `tests/utils/test_scoring.py::test_all_three_signals` (:80).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_compute_entity_boosts linked_memory_ids ENTITY_BOOST_WEIGHT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the max-aggregation + quadratic-popularity-damping formula and the 8-entity/0.5-similarity gates as a unit; adapt the extraction backend and pool size; omit the LLM-based graph-entity variants.
