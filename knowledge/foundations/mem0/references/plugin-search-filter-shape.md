<!-- capsule-v2 -->
# Scoped search filter shape — how do you scope platform memories without letting empty results lie?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** how should a thin REST search client build filters, cut pages, and fail open while keeping rate-limit errors distinguishable from genuine empties?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/_search.py`: `search_memories` (:49-89), `should_rerank` (:18-33), `format_results_for_context` (:92-105). Direct tests `tests/test_search.py` (#22 regression :105-118, silence :121-135, #5684 :138+).
**Signature:** `search_memories(api_key, user_id, project_id, query, metadata_type=None, metadata_filters=None, top_k=3, min_score=0.0, rerank=False, threshold=0.3, global_search=False) -> list[dict]`.
**Data Shape:** scoped filters `{"AND": [{user_id},{app_id},{"metadata":{"type":t}},...]}`; global `{"OR":[{"user_id":"*"}]}`; response unwrapped list-or-`{results}`.

### Decisive source
```python
if global_search:
    filters = {"OR": [{"user_id": "*"}]}
else:
    base_clauses = [{"user_id": user_id}, {"app_id": project_id}]
    ...
    filters = {"AND": base_clauses}
...
results = _do_search(api_key, payload)[:top_k]     # client-side cut AFTER server top_k
if min_score > 0:
    results = [m for m in results if m.get("score", 0) >= min_score]
except Exception as e:                              # incl. HTTPError(429)
    print(f"[mem0] search request failed: {e}", file=sys.stderr)
    return []
```

**Flow:** build filter dialect → POST /v3/memories/search/ (5s timeout) → unwrap → slice to top_k → optional min_score post-filter → on ANY exception: one stderr line + []. `rerank=True` is added ONLY when requested (#5684), but injection paths call `should_rerank()` which defaults ON (REST skips reranking when key omitted; opt out via MEM0_RERANK ∈ {0,false,no,off,""} case-insensitive).
**Invariant:** threshold is a SERVER param; min_score is CLIENT post-filter — they are not interchangeable; empty-by-rate-limit must log status+phrase so it never masquerades as a true empty (#22); happy path emits zero stderr.
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_search.py -q` (11 tests incl. both regressions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "mem0", qualified_name: "mem0.integrations.mem0-plugin.scripts._search.search_memories" });
```

## Verdict
Adopt the AND-scoped/OR-global dialect, double-duty top_k, and loud-empty/fail-open pair for any hosted-memory client; adapt env opt-out names; omit mem0's specific wildcard user semantics if your backend lacks them.
