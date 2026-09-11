<!-- capsule-v2 -->
# Backend result-shape normalization — why does every list() consumer need an unwrap helper?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does the memory layer cope with vector stores that return rows as `[rows]` vs `rows`?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_vector_store_list_rows` (:85-90); inline twin in `_get_all_from_vector_store` (:1329-1340); third variant inlined at :670 and async :2323.
**Signature:** `_vector_store_list_rows(listed)` → flat row list; unwrap rule: if first element is itself a list/tuple, return it, else return the container.
**Data Shape:** Qdrant-style stores return `(rows, next_offset)` tuples; others return bare lists; some wrap once more.

### Decisive source
```python
def _vector_store_list_rows(listed):
    if isinstance(listed, (list, tuple)) and listed and isinstance(listed[0], list):
        return listed[0]        # [[row, row], ...]  ->  [row, row]
    if isinstance(listed, (list, tuple)):
        return listed           # already flat
    return []
```

**Flow:** every place that iterates store rows (entity exact-lookup scans, entity cleanup, get_all, delete_all pages) normalizes through this shape check BEFORE iterating — delete_all additionally indexes `[0]` because it needs only the rows lane of the page tuple.
**Invariant:** the check is structural (is element zero a container?) not provider-keyed, so new backends work without registry edits; empty containers fall through to `[]` rather than raising on `[0]`. A porter who assumes one backend's shape gets either "attribute list has no .payload" crashes or silently iterating a tuple of (rows, offset) where offset isn't a row.
**Probe:** `tests/vector_stores/test_qdrant.py::test_list_with_filters` (:417) pins the wrapped shape; `tests/test_main.py::test_delete_all_paginates_beyond_vector_store_page_size` (:299) exercises tuple-lane indexing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_vector_store_list_rows list unwrap rows payload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt structural unwrapping over provider dispatch; adapt if your ABC standardizes the return shape up front (then delete the helper).
