<!-- capsule-v2 -->
# Dimension lazy pinning — When is a collection's dimensionality written, and what happens on the first query before any add?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Collections are created with `dimension=None` — who sets it, and how do add/query diverge on that path?

## SegmentAPI._validate_dimension
**Path/Symbol:** `chromadb/api/segment.py:_validate_dimension` (:1141-1157), `_validate_embedding_record_set` (:1129-1138), `_query` pre-check (:1000-1001), create_collection `dimension=None` comment (:270).
**Signature:** `_validate_dimension(collection, dim: int, update: bool) -> None`; deliberately NOT traced (would emit thousands of spans per batch).
**Data Shape:** `collection["dimension"]: Optional[int]`; sysdb row updated once; in-memory model mutated after write (`collection["dimension"] = dim`) so subsequent checks in the same request skip the DB.

### Decisive source
```python
if collection["dimension"] is None:
    if update:
        id = collection.id
        self._sysdb.update_collection(id=id, dimension=dim)
        collection["dimension"] = dim
elif collection["dimension"] != dim:
    raise InvalidDimensionException(...)
else:
    return  # all is well
```

**Flow:** ADD/UPDATE/UPSERT pass `update=True` — first write pins the collection's dimension transactionally then caches it. QUERY passes `update=False` (:1000-1001 loops each query embedding) — querying an empty never-written collection raises InvalidDimensionException instead of silently creating a dimension. Segment-level enforcement is a second net (`LocalHnswSegment._ensure_index` raises on dim mismatch).
**Invariant:** Dimension pinning must be exactly-once and visible to all later writers; a porter who lets queries set the dimension creates empty-vector poisoning.
**Probe:** `/tmp/chroma-p1/probe_battery.py` api.dim_lazy_write byte-exact anchor (GREEN); upstream behavior tests under `chromadb/test/api/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_validate_dimension InvalidDimensionException update_collection dimension", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-pins-read-validates; adapt to schema-registry-backed dimension storage; omit the untraced micro-optimization if your tracer samples.
