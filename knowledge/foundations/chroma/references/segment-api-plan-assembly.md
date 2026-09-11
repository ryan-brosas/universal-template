<!-- capsule-v2 -->
# Segment API plan assembly — How does the embedded API translate requests into Scan/Filter/KNN/Limit/Projection plans?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** What is the request-to-plan pipeline a porter must reproduce to keep segment decoupling?

## SegmentAPI._scan / _get / _query plan construction
**Path/Symbol:** `chromadb/api/segment.py:_scan` (:1166-1183), `_get` plan (:725-738), `_query` knn (:1012-1025), `_records` serializer (:1186-1230).
**Signature:** `_scan(collection_id) -> Scan` via `sysdb.get_collection_with_segments`, mapping scope→segment dict (`VECTOR`/`METADATA` required, `RECORD` optional for local).
**Data Shape:** `GetPlan(Scan, Filter(ids,where,where_document), Limit(offset,limit), Projection(...))`; `KNNPlan(Scan, KNN(embeddings,n_results), Filter(None,...), Projection(...))`.

### Decisive source
```python
scope_to_segment = {segment["scope"]: segment for segment in collection_and_segments["segments"]}
return Scan(
    collection=collection_and_segments["collection"],
    knn=scope_to_segment[t.SegmentScope.VECTOR],
    metadata=scope_to_segment[t.SegmentScope.METADATA],
    # Local chroma do not have record segment, and this is not used by the local executor
    record=scope_to_segment.get(t.SegmentScope.RECORD, None),
)
...
return self._executor.knn(
    KNNPlan(scan, KNN(query_embeddings, n_results),
            Filter(None, where, where_document),
            Projection("documents" in include, "embeddings" in include,
                       "metadatas" in include, "distances" in include, "uris" in include)))
```

**Flow:** every read = validate → quota → scan (one sysdb round-trip resolving BOTH segments) → executor plan; every write = validate → `_validate_embedding_record_set` (dimension) → producer submit — writes NEVER touch segments directly, only WAL records. `_records()` folds parallel id/embedding/metadata/document/uri lists into OperationRecords, injecting documents as `chroma:document` and uris as `chroma:uri` metadata keys (the same keys the metadata reader and FTS table special-case).
**Invariant:** Segments communicate exclusively through plans and WAL records; direct cross-segment calls would break the distributed swap-in of the Rust worker.
**Probe:** `/tmp/chroma-p1/probe_battery.py` api.plan anchors (scan scope map + delete GetPlan path GREEN); upstream `chromadb/test/api/` plan tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_scan GetPlan KNNPlan Projection Filter SegmentScope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt plan-mediated reads + WAL-only writes; adapt operator dataclasses to your IR; omit telemetry/quota middleware layers.
