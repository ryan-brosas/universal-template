<!-- capsule-v2 -->
# rerank-window-pagination — how do deep pages survive rerank-based block fetching?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** Why must the candidate window be an exact multiple of page_size, and how is the page extracted?

## Page-aligned candidate window
**Path/Symbol:** `Dealer._rerank_window` `rag/nlp/search.py:555-578`; consumption in `Dealer.retrieval` `rag/nlp/search.py:608-621` and `:719-721`.
**Signature:** `_rerank_window(page_size: int, top: int = 0) -> int` (staticmethod).
**Data Shape:** window = ceil(64/page_size)*page_size; capped by ceil(top/page_size)*page_size when a reranker is active; degenerate page_size<=1 → min(30, top) or 30.

### Decisive source
```python
def _rerank_window(page_size: int, top: int = 0) -> int:
    """Candidate-window size shared by retrieval's block fetch and slice.
    ...
    For those two to agree the window MUST be an exact multiple of
    ``page_size``; otherwise blocks and pages drift apart and deep
    pagination silently drops results and returns short pages.
    """
    if page_size <= 1:
        return min(30, top) if top > 0 else 30
    window = math.ceil(64 / page_size) * page_size
    if top > 0:
        window = min(window, math.ceil(top / page_size) * page_size)
    return window
```

**Flow:** retrieval computes `global_offset=(page-1)*page_size`, fetches ONE backend block at `req["page"]= global_offset//RERANK_LIMIT + 1`, `req["size"]=RERANK_LIMIT`, ranks the whole block, filters by threshold into `valid_idx`, then slices `begin=global_offset % RERANK_LIMIT; end=begin+page_size; page_idx=valid_idx[begin:end]`. Docstring documents the failure mode verbatim.
**Invariant:** window ≡ 0 (mod page_size); breaking it makes block index and slice offset disagree so deep pages silently return short/empty results (no exception). The same invariant has an independent Go twin with its own direct test: `internal/engine/elasticsearch/chunk.go:2907-2921 rerankWindow` + `chunk_test.go:474-484 TestRerankWindowIsPageAligned`.
**Probe:** `sed -n '556,567p' rag/nlp/search.py | grep -c 'MUST be an exact multiple'` → `1`; `grep -n 'begin = global_offset % RERANK_LIMIT' rag/nlp/search.py` → 1 hit :719; Go twin `grep -cn 'TestRerankWindowIsPageAligned' internal/engine/elasticsearch/chunk_test.go` → `1`. All executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "_rerank_window candidate window page_size multiple", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the round-up-to-page-multiple window and the single-block fetch/slice contract; adapt the ~64-candidate pool constant; omit the Go twin when porting only the Python side but keep both tests as spec.
