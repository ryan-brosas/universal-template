<!-- capsule-v2 -->
# Delete-by-filter limit slice — How does delete enforce limit and forbid unconditional wipes?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** `_delete` accepts ids/where/where_document/limit — what are the exact guard clauses a compatible port must implement?

## SegmentAPI._delete
**Path/Symbol:** `chromadb/api/segment.py:_delete` (:740-831).
**Signature:** `_delete(collection_id, ids=None, where=None, where_document=None, limit=None, ...) -> DeleteResult(deleted=int)`.
**Data Shape:** Filtered deletes resolve IDs via a GetPlan FIRST (`_executor.get(GetPlan(scan, Filter(ids, where, where_document)))["ids"]`), then submit DELETE records to the WAL — deletes are asynchronous records, not in-place row kills.

### Decisive source
```python
# You must have at least one of non-empty ids, where, or where_document.
if (ids is None or (ids is not None and len(ids) == 0))
        and (where is None or (where is not None and len(where) == 0))
        and (where_document is None or ...):
    raise ValueError("""You must provide either ids, where, or where_document to delete. ...""")
...
if (where or where_document) or not ids:
    ids_to_delete = self._executor.get(...)...["ids"]
else:
    ids_to_delete = ids

if limit is not None:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit must be a non-negative integer")
    if where is None and where_document is None:
        raise ValueError("limit can only be specified when a where or where_document clause is provided")
    ids_to_delete = ids_to_delete[:limit]
```

**Flow:** empty-everything guard → optional filter resolution → limit validation (bool explicitly NOT an int; limit requires a filter clause so it can never truncate an explicit id list silently) → prefix slice → zero-match short-circuit returns `DeleteResult(deleted=0)` without touching the WAL.
**Invariant:** Deleting "everything" is impossible via this API — you must name targets; count returned equals sliced list length even though actual removal happens later in segments.
**Probe:** `/tmp/chroma-p1/probe_battery.py` api.delete_guard + api.limit_slice anchors (GREEN); upstream `chromadb/test/api/test_api.py` delete matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_delete ids_to_delete limit DeleteResult guard", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the guard ladder verbatim for API parity; adapt filtered resolution to your planner; omit product telemetry capture events.
