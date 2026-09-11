<!-- capsule-v2 -->
# Reranker contract — how does an optional reranker attach without ever breaking the search path?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** what is the minimal reranker interface and its failure contract?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/base.py`: `BaseReranker.rerank` (:8-20); five backends (`cohere_reranker.py` :37-93, `llm_reranker.py`, `huggingface_reranker.py`, `sentence_transformer_reranker.py`, `zero_entropy_reranker.py`); wired in `Memory.__init__` (main.py :505-511) and `search` (:1500-1505).
**Signature:** `rerank(query: str, documents: List[Dict], top_k: int = None) -> List[Dict]` — documents carry a `memory` (fallback `text`/`content`) field; returns reordered docs with `rerank_score` added.
**Data Shape:** constructed via `RerankerFactory` from provider name + config/dict; optional on `MemoryConfig.reranker` (None ⇒ skipped entirely).

### Decisive source
```python
# main.py search():
if rerank and self.reranker and original_memories:
    try:
        reranked_memories = self.reranker.rerank(query, original_memories, limit)
        original_memories = reranked_memories
    except Exception as e:
        logger.warning(f"Reranking failed, using original results: {e}")
# cohere_reranker fallback:
except Exception as e:
    logger.warning("Cohere reranking failed, falling back to original order: %s", e)
    for doc in documents:
        fallback_doc = doc.copy()
        fallback_doc['rerank_score'] = 0.0
    return fallback_docs[:final_top_k] if final_top_k else fallback_docs
```

**Flow:** hybrid-scored results → if caller asked AND a reranker is configured AND there are results → rerank → replace list; any exception at either layer (call-site or inside backend) degrades to the pre-rerank order. Backends copy docs before mutating so the caller's list is never aliased.
**Invariant:** double-layered fail-open — the memory layer catches, AND each backend catches internally returning score-stamped originals; reranking runs AFTER fusion/threshold/top-k, so it reorders within one page but can never rescue filtered-out memories; `rerank=False`/no-config costs nothing.
**Probe:** `tests/rerankers/` suites; call-site semantics pinned by search tests in `tests/test_main.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "BaseReranker rerank rerank_score RerankerFactory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-method contract + fail-open double-guard + post-fusion position; adapt backend implementations freely.
