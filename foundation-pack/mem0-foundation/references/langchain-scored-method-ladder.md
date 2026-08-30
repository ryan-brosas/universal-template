<!-- capsule-v2 -->
# Langchain adapter scored-method ladder — how does an untyped vectorstore wrapper never return a None score into threshold ranking?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how do you adapt an arbitrary LangChain VectorStore to the OutputData(score) contract when score availability varies per concrete backend?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/langchain.py`: `_SCORED_BY_VECTOR_METHODS` (:27-31), `Langchain.search` (:104-141), fallback constant at :137, `update` (:149-154).
**Signature:** `search(query: str, vectors: List[List[float]], top_k: int = 5, filters=None) -> List[OutputData]`.
**Data Shape:** client = any langchain_community VectorStore instance; the adapter duck-types three optional scored-search methods (not in the base contract) then degrades to the unscored one.

### Decisive source
```python
_SCORED_BY_VECTOR_METHODS = [
    "similarity_search_by_vector_with_relevance_scores",  # Chroma
    "similarity_search_with_score_by_vector",             # FAISS, Qdrant
    "similarity_search_by_vector_with_score",             # Pinecone, YDB
]
...
for method_name in _SCORED_BY_VECTOR_METHODS:
    method = getattr(self.client, method_name, None)
    if method is None:
        continue
    try:
        results = method(**kwargs)
        return [...score=float(score)...]
    except (NotImplementedError, TypeError):
        continue
# Fallback ... Assign 1.0 so score_and_rank never receives None (None < threshold crashes).
docs = self.client.similarity_search_by_vector(**kwargs)
return [OutputData(..., score=1.0, ...) for doc in docs]
```

**Flow:** search tries each scored method in order — first present-and-working wins → NotImplementedError/TypeError from abstract or incompatible implementations advance the ladder → final fallback returns UNSCORED documents stamped score 1.0 → list()/get() route through `_parse_output`, which ALSO duck-types Document lists (metadata→payload, id attr, no score).
**Invariant:** search results must NEVER carry score=None because mem0's fusion compares scores against thresholds (`None < threshold` raises TypeError inside score_and_rank) — the 1.0 stamp is deliberate pass-through semantics ("kept, not ranked"), not a relevance claim; method presence is probed with getattr (never hasattr chains that swallow attribute errors); update() composes as delete+insert because LangChain has no native upsert-by-id.
**Probe:** `grep -n "_SCORED_BY_VECTOR_METHODS" mem0/vector_stores/langchain.py` (:27 def + :114 use); `grep -n "score=1.0" mem0/vector_stores/langchain.py` (exactly :137); `grep -n "never receives None" mem0/vector_stores/langchain.py`.
**Direct test:** `tests/vector_stores/test_langchain_vector_store.py::test_search_score_is_never_none` (:232), `test_search_uses_scored_method_when_available` (:252), `test_search_falls_back_when_scored_method_raises_not_implemented` (:268), `test_update_wraps_vector_and_payload_in_lists` (:282).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_SCORED_BY_VECTOR_METHODS Langchain similarity_search_by_vector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the probe-ladder + neutral-score-stamp shape for any capability-varying adapter surface; adapt the method roster and neutral value to your contract; letting None reach ranking reintroduces the documented crash. Fully direct-tested at this pin (no caveat).
