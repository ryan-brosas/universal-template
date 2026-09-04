<!-- capsule-v2 -->
# Reranker doc-text extraction funnel — which key wins when documents carry different text keys?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does a reranker turn heterogeneous result dicts into plain strings for the scoring backend, and what happens to dicts with none of the known keys?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/cohere_reranker.py`: `CohereReranker.rerank` extraction loop (:59-66); identical block in `mem0/reranker/zero_entropy_reranker.py` (:63-70) and `mem0/reranker/sentence_transformer_reranker.py` (:79-86); per-doc scalar form in `mem0/reranker/llm_reranker.py` (:113-121).
**Signature:** inline ladder over each doc: `'memory' in doc` → `'text' in doc` → `'content' in doc` → else `str(doc)`.
**Data Shape:** input is the pipeline's projected result dicts (`{'memory': str, ...}`, optionally `score`, metadata); output is a parallel `doc_texts: list[str]` (or one `doc_text` per iteration in llm_reranker).

### Decisive source
```python
for doc in documents:
    if 'memory' in doc:
        doc_texts.append(doc['memory'])
    elif 'text' in doc:
        doc_texts.append(doc['text'])
    elif 'content' in doc:
        doc_texts.append(doc['content'])
    else:
        doc_texts.append(str(doc))
```

**Flow:** per document, first matching key wins (`memory` beats `text` beats `content`) → a dict with NONE of them degrades to its full `repr()` via `str(doc)` — never dropped, never KeyError.
**Invariant:** the funnel NEVER raises on unexpected shapes and preserves positional order 1:1 with `documents`; a naive port that indexes `doc['memory']` directly crashes on generic dicts, and one that filters unknown-shape docs silently shrinks the result set below what the fallback path promises. The `str(doc)` repr tail is load-bearing for pass-through callers that re-join texts to docs by index.
**Probe:** `grep -c "doc_texts.append" mem0/reranker/cohere_reranker.py mem0/reranker/zero_entropy_reranker.py mem0/reranker/sentence_transformer_reranker.py` — exactly **4 lines per file** (3 keyed + 1 `str(doc)`; total 12 across the trio).
**Coverage caveat (scoped):** `test_reranker_public_exports.py` pins all six family exports via `mem0.reranker.__all__`; the funnel itself is exercised through the LLM reranker's `test_text_field_extraction` (:92) / `test_content_field_extraction` (:102); no test pins the 4-line funnel shape directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "doc_texts append memory text content reranker", limit: 10 });
```

## Verdict
Adopt the ordered first-match-wins funnel ending in `str(doc)` for any reranker over mem0-shaped results; adapt the key set to your own projection vocabulary; omit nothing — the fallback branch is the porting trap.
