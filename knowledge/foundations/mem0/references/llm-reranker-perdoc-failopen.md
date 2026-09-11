<!-- capsule-v2 -->
# LLM reranker per-doc fail-open — one bad completion costs 0.5, never the batch

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** when the LLM call for ONE document fails or times out, what does the reranker do to the remaining documents?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/llm_reranker.py`: `LLMReranker.rerank` loop (:104-160); nested `llm` config resolution (:52-66).
**Signature:** `rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]`.
**Data Shape:** sequential (not batched) generate_response per document; failure ⇒ that doc gets `rerank_score = 0.5` and the loop CONTINUES.

### Decisive source
```python
except Exception as e:
    # Fallback: assign neutral score if scoring fails
    logger.warning("LLM reranking failed for a document, assigning neutral score: %s", e)
    scored_doc = doc.copy()
    scored_doc['rerank_score'] = 0.5
    scored_docs.append(scored_doc)
...
scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
```

**Flow:** try {truncate → build user message → generate → extract} per doc; any exception ⇒ warn + neutral 0.5 + continue → after ALL docs are scored, sort descending and apply top_k (`if top_k:` … `elif self.config.top_k:`).
**Invariant:** this is PER-DOCUMENT fail-open with a NON-ZERO neutral (0.5) — deliberately different from the API-backed siblings' BATCH fallback (whole-list 0.0, see `reranker-contract`). A naive port that wraps the whole loop in one try/except turns a single rate-limit into an all-0.0 no-op ranking; a port using neutral 0.0 would sink failed docs below every honest low-relevance doc. Config plumbing worth keeping: a nested `config.llm` dict overrides provider/config wholesale (for Ollama-style providers needing extra fields) via `LlmFactory.create`, and a custom `scoring_prompt` is accepted but emits a DeprecationWarning and becomes the system message.
**Probe:** `grep -cF "scored_doc['rerank_score'] = 0.5" mem0/reranker/llm_reranker.py` (=1); `grep -cF 'if top_k:' mem0/reranker/llm_reranker.py` (=1).
**Probe (direct test):** `tests/rerankers/test_llm_reranker_rerank.py::test_llm_failure_is_logged_and_falls_back` lives in `tests/rerankers/test_reranker_failure_logging.py:15` (warn + continue pinned); sort/top_k order pinned by `test_documents_sorted_by_score_descending` (:54) and the two top_k tests (:72/:82); nested-config override matrix in `test_llm_reranker_nested_config.py` (9 `test_nested_llm_*` cases + 1 acceptance test in `test_llm_reranker_config.py`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "LLMReranker generate_response neutral score warning", limit: 10 });
```

## Verdict
Adopt per-doc try/except with neutral 0.5 continuation for any LLM-judge ranking loop; adapt the nested-config override shape to your factory; omit batch-level exception wrapping — it changes the degradation semantics this design exists to provide.
