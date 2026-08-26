<!-- capsule-v2 -->
# RRF hybrid fusion — how do you merge dense + lexical result lists without comparing their incompatible score scales?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does reciprocal rank fusion require to stay deterministic and score-threshold-safe when fusing a BM25 leg with a cosine leg?

## Rank-based additive fusion on (filename, page, text) identity
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:468-555` (`_rrf_fuse`), `:555-587` (`_rrf_fuse_lists`, N-leg variant).
**Signature:** `_rrf_fuse(dense: list[SearchResult], lexical: list[SearchResult], k_rrf: int = 60) -> list[SearchResult]`; `_rrf_fuse_lists(result_lists: list[list[SearchResult]], k_rrf: int = 60) -> list[SearchResult]`.
**Data Shape:** Documents identified by `(filename, page, text)` — same key as cross-scope dedup. Per-leg observability stamped ON the SearchResult in place: `dense_rank`, `lexical_rank`, `rrf_score` (rounded to 6dp). Empty-leg short-circuit returns the other list unchanged.

### Decisive source
```python
# engine.py:473-486 — the three properties that matter
#   - Rank-based, NOT score-based — defends against score-distribution
#     drift between the two legs. Lexical BM25 and dense cosine live
#     in different scales; comparing raw values would be unsound.
#   - Both legs contribute additively; a chunk that ranks moderately
#     in BOTH legs is preferred over a chunk that ranks #1 in only one leg.
#   - k_rrf=60 is the literature default (Cormack 2009). Smaller k boosts
#     top ranks; larger k flattens.
s += 1.0 / (k_rrf + rank)   # per leg where doc appears
```
Two subtleties a porter gets wrong: (1) iterating DENSE first when building the items map means a chunk present in both legs keeps the dense-side SearchResult object — which carries the dense score in `.score`, so downstream `score_threshold` semantics are unchanged by fusion; (2) tie-breaking is `(−rrf_score, filename, page)` with None→−1 so identical queries produce IDENTICAL orderings across runs. The N-leg variant (`_rrf_fuse_lists`, used for query-transform multi-query fan-out) accumulates scores into the FIRST list's object — callers must pass the base hybrid result first for the same threshold reason.

**Flow:** dense + lexical ranked lists → identity-keyed merge keeping per-leg ranks → additive `1/(k+rank)` scoring → in-place stamping of observability fields → deterministic sort → new list (same object identities).
**Invariant:** Never compare or mix raw leg scores; `.score` stays the dense score after fusion; fused ordering must be deterministic (explicit non-score tie-break).

**Probe:** `tests/unit/test_knowledge_envelope_rank_fields.py::test_rrf_score_populated_surfaces_on_chunk / test_both_per_leg_ranks_surface_when_present / test_no_rank_fields_when_rrf_is_none` — pins that ranks surface only when RRF actually fused.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "rrf_fuse reciprocal rank fusion dense lexical", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rank-based fusion with identity-keyed dedup, dense-first object retention, and deterministic tie-breaks. Adapt k_rrf only with measurement. Omit per-leg rank stamping if you have no wire consumers.
