<!-- capsule-v2 -->
# Hybrid chunk lane — RRF over (chunk, summary) pairs with factor composition

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you fuse vector chunk hits with their LLM summaries into one ranking where importance/truth/personal factors multiply without breaking baseline order?

## rank_chunk_summary_pairs
**Path/Symbol:** `cognee/modules/retrieval/hybrid/ranking.py:rank_chunk_summary_pairs` (:8-58), `_rrf_k` (:61-62), `_importance_factor` (:65-69); pair builder `hybrid/pairs.py:chunk_summary_pairs` (:15-59); driver `hybrid_retriever.py:_retrieve_one` (:103-144).
**Signature:** `(pairs, limit, use_importance_weight, use_truth_weight=False, q_coords=None, truth_state_by_id=None, current_truth_epoch=None, personal_weights=None, personal_influence=0.0) -> list[dict]`.
**Data Shape:** Pair = `{chunk_id, chunk_text, summary_id, summary_text, chunk, vector_rank, summary_rank}`; summaries join via payload `source_chunk_id`, or by RECOMPUTING the deterministic summary id `uuid5(chunk_uuid, "TextSummary")`.

### Decisive source
```python
rrf_score = sum(1.0 / (rrf_k + rank + 1) for rank in ranks)   # ranks present on either channel
final_score = rrf_score
if use_importance_weight: final_score *= _importance_factor(chunk)   # 0.75 + 0.5*clamp(importance)
if use_truth_weight and q_coords and current_truth_epoch is not None:
    if truth_state.get("truth_epoch") == current_truth_epoch:
        final_score *= truth_factor(truth_state.get("truth_alignment", []), q_coords)
if personal_weights:
    w = personal_weights.get(chunk_id)
    if w is not None:
        final_score *= personal_factor(w, personal_influence, distance_space=False)
ranked.append((final_score, rrf_score, min(ranks), chunk_id, pair))
ranked.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
def _rrf_k(chunks_top_k): return max(30, min(60, 20 + 2 * chunks_top_k))
```

**Flow:** gather `DocumentChunk_text` (limit 2×top_k) and `TextSummary_text` hits concurrently → build pairs keyed by chunk id/text → batch-retrieve missing source chunks for summary-only pairs → rank → lazily load summary text for ranked pairs (validating node filters per row). Entity lane runs CONCURRENTLY with the whole chunk lane (`asyncio.gather`).
**Invariant:** (1) Empty personal-weight map must be BYTE-IDENTICAL to unpersonalized runs — weights only multiply when a matching id exists (fail-open contract, tested). (2) Truth factor applies ONLY to vectors whose truth_epoch equals the query's epoch; unknown epochs never boost. (3) Tie-break ladder (final, rrf, min-rank, id) makes ordering deterministic. (4) rrf_k scales with top_k but clamps to [30, 60].
**Probe:** `cognee/tests/unit/modules/retrieval/hybrid/test_personal_weight_ranking.py::test_personal_weights_compose_with_importance_and_truth_factors`, `::test_empty_personal_weight_map_is_byte_identical_to_baseline`; `hybrid/test_truth_epoch_ranking.py::test_truth_weight_only_applies_to_current_epoch_vectors`; `hybrid_facts_test.py` (17 tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "rank_chunk_summary_pairs rrf importance personal weight factor", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt RRF pair fusion + multiplicative fail-open factors + deterministic tie-breaks; adapt channel collections to your stores; omit truth/personal layers unless you run those subsystems.
