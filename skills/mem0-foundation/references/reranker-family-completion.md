<!-- capsule-v2 -->
# Reranker family completion — five backends, one contract, three truncation/failure variants

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how do the remaining reranker backends (Cohere, ZeroEntropy, SentenceTransformer, LLM) complete the family whose ABC + HuggingFace sibling are already mined, and where do their top-k / failure semantics deliberately differ?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/cohere_reranker.py` (92L), `mem0/reranker/zero_entropy_reranker.py` (103L), `mem0/reranker/sentence_transformer_reranker.py` (119L), `mem0/reranker/llm_reranker.py` (172L); all subclass `mem0/reranker/base.py:BaseReranker` (19L, one abstract `rerank`).
**Signature:** shared `rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]` — every backend stamps `rerank_score` onto COPIES and never mutates inputs.
**Data Shape:** in: projected result dicts + optional top_k; out: ranked dicts with `rerank_score: float`.

### Decisive source
```python
# cohere_reranker.py — server-side cut:
top_n=top_k or self.config.top_k or len(documents),
# zero_entropy_reranker.py — client-side cut after explicit sort:
reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
reranked_docs = reranked_docs[:top_k]
# llm_reranker.py — per-doc scoring loop, neutral on failure:
scored_doc['rerank_score'] = 0.5   # vs 0.0 batch fallback in API siblings
```

**Flow:** every implementation: empty-docs short-circuit (`if not documents: return documents`) → text extraction funnel → score → order → truncate. The VARIANTS are the seam: Cohere cuts server-side (`top_n` ladder ending `len(documents)` = return-all-reordered); ZeroEntropy has no top_n param so it sorts client-side then slices; SentenceTransformer scores locally via CrossEncoder pairs and slices after sort; LLM calls generate_response per doc with 4000-char input caps and a decimal-first→clamp→0.5 extraction ladder.
**Invariant:** all four share the batch-level fail-open contract (exception ⇒ original-order copies stamped 0.0, sliced to `final_top_k if final_top_k else all`) EXCEPT LLMReranker, which degrades per-document at neutral 0.5 — porting the wrong granularity either no-ops a whole ranking on one rate-limit or sinks failed docs below every honest result. Init-time key requirements differ per family (COHERE_API_KEY / ZERO_ENTROPY_API_KEY env-or-config with hard ValueError; local models need no keys) but all raise ImportError at construction when their SDK is absent.
**Probe:** `grep -cF 'return fallback_docs[:final_top_k] if final_top_k else fallback_docs' mem0/reranker/cohere_reranker.py mem0/reranker/zero_entropy_reranker.py mem0/reranker/sentence_transformer_reranker.py` (=1 each; sum 3); `grep -c "doc_texts.append" mem0/reranker/cohere_reranker.py mem0/reranker/zero_entropy_reranker.py mem0/reranker/sentence_transformer_reranker.py` (=4 each; sum 12); `grep -cF 'if not documents:' mem0/reranker/llm_reranker.py` (=1).
**Coverage caveat (scoped):** `tests/rerankers/` (plural) DOES exist — 8 files pin the family's LLM/config/fallback/no-mutation surfaces (`test_llm_reranker_rerank.py`, `test_reranker_fallback_topk.py`, `test_reranker_fallback_no_mutation.py`, `test_reranker_failure_logging.py`, `test_reranker_public_exports.py`, + nested-config matrix); what has NO dedicated suite is the Cohere/ZeroEntropy happy-path API call shape and BOTH SentenceTransformer methods — those remain source-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "Reranker BaseReranker rerank rerank_score fallback", limit: 10 });
```

## Verdict
Adopt the family contract (copy-on-stamp, empty short-circuit, fail-open) with each backend's truncation variant kept DISTINCT; adapt provider SDK surfaces freely; omit any unification that moves the top-k cut or changes the 0.0-vs-0.5 degradation granularity.
