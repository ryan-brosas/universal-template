<!-- capsule-v2 -->
# Cosine tool shortlister — how do you rank a 300-tool catalogue without an LLM call, and never strand the agent with an empty result?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#624); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does it take to swap an LLM ranker for embeddings at runtime — backend residency, vector caching, query/context blending, and the empty-result trap?

## EmbeddingShortlister
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/shortlister/embedding.py:225-380` (`EmbeddingShortlister`, `_require_backend`, `_document_matrix`, `_query_vector`, `_select`, `warm`), backends :88-149 (`_LocalBackend`, `_OpenAIBackend`), lifecycle :152-214 (`is_ready`, `prewarm`, `ensure_loading`, `reset_caches`, `_RETRY_COOLDOWN_S = 30.0`, `_MIN_FALLBACK_RESULTS = 3`), `_normalize` :217-222; doc construction `doc.py:35-150` (`split_identifier`, `tool_document`, `tool_fingerprint`, `app_name_for_tool`).
**Signature:** `async shortlist(request: ShortlistRequest) -> ShortlistResult`; `async warm(tools) -> int`; `tool_fingerprint(document: str, model_name: str) -> str` (sha256 over model + document).

### Decisive source
```python
# embedding.py:318-339 — selection ladder with the never-empty rule
def _select(self, scores, tools, request):
    limit = request.top_k if request.top_k else len(tools)
    if request.max_results:
        limit = min(limit, request.max_results)
    limit = max(1, min(limit, len(tools)))
    order = np.argsort(-scores)[:limit]
    kept = [(int(i), float(scores[i])) for i in order if float(scores[i]) >= self._min_score]
    if not kept:
        # Nothing cleared the floor. Returning nothing is worse than
        # returning the best guesses: the agent has no next move, and the
        # bind-time cap raises on an empty ranking.
        fallback = min(_MIN_FALLBACK_RESULTS, limit, len(tools))
        kept = [(int(i), float(scores[i])) for i in order[:fallback]]
    return kept
```
```python
# embedding.py:292-314 — blend as weighted unit vectors, NOT string concat
# String concatenation would let a long task context dominate a short step
# query — the weighting would become an accident of relative length.
texts = [t for t in (step, context) if t]      # empty query => None (NOT unavailable)
normalized = _normalize(await backend.aembed(texts, as_query=True))
if len(texts) == 1: return normalized[0]
blended = alpha * normalized[0] + (1.0 - alpha) * normalized[1]   # alpha=query_weight 0.7
return _normalize(blended)[0]
```

**Flow:** documents are built per tool from SPLIT identifiers (`crm_get_contacts_contacts_get` → "crm get contacts contacts get" — camel/snake boundaries split; duplicate words KEPT as genuine emphasis) + description + param lines + response field names; args_schema JSON/response schemas are deliberately EXCLUDED ("in a fixed-size vector they dilute signal rather than add it"). Vectors cached in module-level `_VECTORS` keyed by content fingerprint sha256(backend_key \0 document) — an edited description or changed model re-embeds automatically; fingerprint includes the BACKEND key because two providers serving one model name produce different vector spaces. Missing fingerprints embed in ONE batched call; scoring is a single matmul `document_matrix @ query_vector`. Local backend shares the process-wide fastembed session via `get_shared_text_embedding` (one ONNX session for knowledge+policy+shortlister); asymmetric models (BAAI/bge-* minus *reranker*) get query_embed vs passage_embed methods, symmetric ones plain embed. A not-ready backend raises `ShortlisterUnavailableError` AFTER kicking a background load thread (`ensure_loading`, 30s retry cooldown after failure) so the caller degrades to LLM for that one call and later calls get cosine.

**Invariant:** (1) NEVER return empty: below-floor results fall back to the best `min(3, N)` — an empty find_tools result is a dead end and cap.py raises on an empty bind ranking; this is a cosine-strategy property, NOT a seam guarantee (the LLM strategy may legitimately return nothing). (2) An empty/blank query returns no candidates WITHOUT raising unavailability — the fallback strategy would receive the same empty query, so raising would be wrong. (3) A query must never block on a model download (mirrors knowledge/reranker.py): degrade first, load in background. (4) Vectors stored L2-normalized with zero rows guarded (`norms[norms == 0] = 1.0`) so zero vectors score 0, never NaN. (5) `warm()` blocks deliberately — boot time only, never on a query; cache misses mean incremental re-warms embed only new tools.

**Probe:** direct tests `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_shortlister_embedding.py::test_never_returns_empty_even_when_nothing_clears_min_score` (:126), `::test_blank_query_returns_nothing_rather_than_claiming_unavailability` (:208), `::test_query_and_task_context_are_embedded_separately` (:174), `::test_changed_description_reembeds` (:240), `::test_unloaded_model_raises_unavailable_and_starts_background_load` (:252), `::test_failed_load_sets_a_retry_cooldown` (:266), `::test_bge_backend_uses_query_and_passage_encoders` (:305), `::test_unknown_provider_is_unavailable_not_silently_ignored` (:331); doc tests `tests/test_shortlister_doc.py` (identifier splitting + determinism).

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "EmbeddingShortlister shortlist tool_fingerprint ensure_loading", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT the recall-ranker pattern wholesale when cutting any large candidate list before an expensive judge (LLM rerank, human review): split identifiers before embedding, cache by content hash, blend contexts as vectors, and keep a best-effort floor under empty results.
