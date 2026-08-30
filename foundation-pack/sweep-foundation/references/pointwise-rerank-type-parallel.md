<!-- capsule-v2 -->
# Pointwise per-type rerank — how do you run an external reranker per snippet category with frozen top ranks and a parallel/sequential fallback?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do you keep the best hybrid results authoritative while letting a reranker reorder the tail, and what happens when the executor dies mid-fan-out?

## get_pointwise_reranked_snippet_scores: frozen top-5, rescaled tail, ThreadPoolExecutor with sequential fallback
**Path/Symbol:** `sweepai/utils/ticket_utils.py:get_pointwise_reranked_snippet_scores` (:221–288); orchestration loop in `multi_prep_snippets` (:335–407); `process_snippets` adapter (:290–294).
**Signature:** `get_pointwise_reranked_snippet_scores(query, snippets, snippet_scores, NUM_SNIPPETS_TO_KEEP=5, NUM_SNIPPETS_TO_RERANK=100, directory_summaries={}) -> dict[str, float]`.
**Data Shape:** In/out: `denotation -> float` score dicts; per type a subset list sorted by hybrid score; reranker response items are `(index, relevance_score)` pairs.

### Decisive source
```python
if not COHERE_API_KEY and not VOYAGE_API_KEY:
    return snippet_scores                       # no keys ⇒ identity
new_snippet_scores = {d: v / 1_000_000_000_000 for d, v in rerank_scores.items() ...}
response = cohere_rerank_call(...) or voyage_rerank_call(...)
for document in response.results:               # ranks 6..100 ← reranker (digit-penalized)
    new_snippet_scores[...] = apply_adjustment_score(..., document.relevance_score)
for snippet in sorted_snippets[:NUM_SNIPPETS_TO_KEEP]:   # top 5 FROZEN ×1000
    new_snippet_scores[snippet.denotation] = rerank_scores[snippet.denotation] * 1_000

# multi_prep_snippets :351-360 — parallel by type with fallback:
with ThreadPoolExecutor() as executor:
    future_to_type = {executor.submit(process_snippets, t, ...): t for t, sub in separated_snippets}
    ...
except RuntimeError as e:                        # interpreter shutdown etc.
    logger.warning(e)                            # → identical calls, sequentially
```

**Flow:** per category (source/tests/docs/tools/deps — never junk): sort by hybrid score → serialize top-100 as fenced code plus deepest directory-summary context → squash ALL existing scores ÷10¹² as baseline → call Cohere first, Voyage only if Cohere key absent → write reranker scores over the squashed baseline → re-freeze original top-5 at ×1000 so they can never be displaced → back in the caller, per-type cutoff ladder keeps at most `type_to_result_count[t]`, breaking at percentile<floor or absolute-score<floor, then AnalyzeSnippetAgent filters non-source types; if EVERY type empties out, fall back to raw top-count lists preferring source.
**Invariant:** The frozen-top-K override happens AFTER the reranker writes scores — reranker output for ranks 1–5 is computed but discarded. Score scales are deliberately incomparable across stages (÷10¹² baselines vs ×1000 frozen vs raw relevance), and only within-dict order matters because each dict is consumed by its own sort. `RuntimeError` from a dying executor downgrades to sequential execution with IDENTICAL arguments — results must not depend on which path ran.
**Probe:** No offline unit test (needs reranker API keys — coverage caveat). Deterministic probes at pin: `grep -c '1_000_000_000_000' sweepai/utils/ticket_utils.py` → 1; `grep -n 'NUM_SNIPPETS_TO_KEEP\]' sweepai/utils/ticket_utils.py` → :281–282 frozen block.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "sweep", function_name: "sweep.sweepai.utils.ticket_utils.get_relevant_context", direction: "both", depth: 2 });
// executed at pin: get_relevant_context callees include ChatGPT.chat_anthropic,
// RepoContextManager.boost_snippets_to_top, Snippet.expand; sole caller fetch_relevant_files
```

## Verdict
Adopt frozen-authoritative-top-K + rescaled-reranked-tail per category, key-based provider selection, and the parallel-with-identical-sequential-fallback pattern around external ranking APIs. Adapt budgets/floors via your taxonomy tables. Omit directory-summary enrichment if you don't maintain repo tree summaries.
