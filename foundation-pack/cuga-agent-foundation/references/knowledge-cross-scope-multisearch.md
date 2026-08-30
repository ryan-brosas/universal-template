<!-- capsule-v2 -->
# Cross-scope multi-search fusion — how do you merge ranked lists from multiple collections without letting one scope starve another, and what does per_scope_limit toggle?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What is the exact pipeline (fan-out → RRF → dedup → budget) that merges per-scope search results, and which failure/budget invariants must a porter preserve?

## gather(return_exceptions=True) → cross-scope RRF k=60 → hash-key dedup → Option B or F budget
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:3452-3675` (`KnowledgeEngine.search_multi`); stats carrier `_MultiSearchStats` (`by_scope`, `top_score_by_scope`, `failed_scopes`, `partial`, per-scope `dedup_collapses`).
**Signature:** `async def search_multi(self, scoped_collections: list[tuple[str, str]], query, limit=10, score_threshold=0.0, per_scope_limit=True) -> tuple[list[SearchResult], _MultiSearchStats]`.
**Data Shape:** dedup key = `(filename, page, sha1(text)[:16])`; every result carries its source scope + `cross_scope_rrf_score = round(1/(60+rank), 6)`; final ordering key `(-cross_scope_rrf, filename, page-or--1)` — deterministic, never insertion-order dependent.

### Decisive source
```python
# engine.py:3492-3494 (contract) and :3614-3626 / :3628-3659 (the two budgets)
# We do NOT raise on partial failure: a degraded answer beats no answer
# when one collection is down.
...
if per_scope_limit:            # Option B -- caller asked for breadth ("all")
    total_cap = min(100, limit * n_scopes)
    for s in non_empty_scopes: merged.extend(post_dedup_by_scope[s][:limit])
    ...
    return merged[:total_cap], stats
# Option F -- fixed total. Each non-empty scope reserves
# min(N_s, ceil(limit/n)); spare capacity redistributes in scope order;
# sum hard-clamped to limit (defends limit=1 with two scopes where
# ceil(1/2)=1 each = 2 slots).
```
Fan-out runs one `search_with_stats` per scope via `asyncio.gather(..., return_exceptions=True)`; failed scopes land in `stats.failed_scopes`, set `partial=True`, and are EXCLUDED from `by_scope` so the wire envelope can distinguish "searched, no hits" from "wasn't searched". Dedup happens BEFORE quota so collapse attribution counts the loser's scope while slots are computed on survivors; tiebreak is higher RRF then higher raw score.

**Flow:** clamp limit to [1,100] → parallel per-scope search → bucket results/stats by scope → stamp cross-scope RRF from in-scope rank → dedup by content hash keeping higher RRF (+score tiebreak), accrue `dedup_collapses` on loser's scope → re-bucket survivors preserving rank order → apply Option B (per-scope cap, total min(100, limit×n)) or Option F (ceil-quota + redistribution + hard clamp) → unified sort by RRF.
**Invariant:** Partial scope failure degrades but never raises; quota modes are semantic promises — B means "I genuinely want both scopes' best" (auto-fallback session→all uses F precisely so the LLM's response-size expectation is preserved); representation quotas must be deterministic (fixed sort keys with filename/page tiebreaks) or eval comparisons drift.

**Probe:** `tests/unit/test_knowledge_search_multi.py` — `test_every_result_carries_its_source_scope` (:79), `test_same_chunk_in_both_scopes_collapses_keeping_higher` (:106), `test_one_scope_erroring_returns_partial_results` (:175), `test_option_b_caps_total_at_hundred_even_with_huge_scopes` (:206), `test_deterministic_tiebreak_on_equal_scores` (:260).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "search_multi per_scope_limit cross_scope_rrf_score dedup_collapses _MultiSearchStats", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole pipeline shape for any federated retrieval over scoped stores. Adapt the stats envelope. Omit Option B if you only ever have the fixed-total contract (keep the clamp). Direct tests pin dedup, partial-failure, cap, and determinism.
