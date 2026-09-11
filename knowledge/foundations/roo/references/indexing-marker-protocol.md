<!-- capsule-v2 -->
# Indexing-complete marker — how does restart distinguish "resume incremental" from "reindex everything"?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How is scan completion persisted inside the collection itself, and what happens with pre-marker indexes?

## A metadata point with a deterministic UUID rides in the collection
**Path/Symbol:** `src/services/code-index/vector-store/qdrant-client.ts:hasIndexedData/markIndexingComplete/markIndexingIncomplete` (:587-683).
**Signature:** `uuidv5("__indexing_metadata__", QDRANT_CODE_BLOCK_NAMESPACE)` — same id for all three methods.
**Data Shape:** marker point = zero-vector of `vectorSize` dims, payload `{type: "metadata", indexing_complete: boolean, started_at | completed_at}`; `initialize()` returns `created: true` after dimension-mismatch recreation.

### Decisive source
```ts
const metadataId = uuidv5("__indexing_metadata__", QDRANT_CODE_BLOCK_NAMESPACE)
const metadataPoints = await this.client.retrieve(this.collectionName, { ids: [metadataId] })
if (metadataPoints.length > 0) {
  return metadataPoints[0].payload?.indexing_complete === true
}
// backward compatibility: no marker → assume complete if any points exist
return pointsCount > 0
```

**Flow:** `startIndexing` marks INCOMPLETE before scanning, COMPLETE only after watcher start succeeds. Orchestrator branches on `hasIndexedData() && !collectionCreated` ⇒ incremental scan (cache-driven skip) vs full scan. Dimension-mismatch recreate DELETES the collection (marker dies with it) ⇒ next start is a full reindex by construction.
**Invariant:** completion state lives in the SAME store as the vectors — never in local config — so any client/workspace pair sees consistent resume semantics; and the marker must be EXCLUDED from search results (the always-merged `must_not type=metadata` clause exists precisely because the marker is a point).
**Probe:** `src/services/code-index/vector-store/__tests__/qdrant-client.spec.ts` ("initialize" describe :515+, mismatch-recreate :592/:897); executed pins: marker uuid count=3 sites, hnsw m=64/ef_construct=512/on_disk×4.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "hasIndexedData markIndexingComplete __indexing_metadata__", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt in-collection completion markers keyed by a deterministic UUID + backward-compat fallback (points_count>0). Adapt HNSW tuning (m=64, ef_construct=512, hnsw_ef 128 at query) to your scale. Omit the legacy no-marker branch if you control genesis.
