<!-- capsule-v2 -->
# pathSegments filter grammar — how are directory-scoped searches and per-file deletes expressed to Qdrant?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How does a `directoryPrefix` become a Qdrant filter, and how do file deletions match points?

## Segment-index equality keys, not prefix matching
**Path/Symbol:** `src/services/code-index/vector-store/qdrant-client.ts:upsertPoints/search/deletePointsByMultipleFilePaths` (:338-375; :399-468; :478-540).
**Signature:** `search(queryVector: number[], directoryPrefix?: string, minScore?: number, maxResults?: number)`.
**Data Shape:** every point payload gains `pathSegments = {"0": seg0, "1": seg1, ...}` (relative path split on `path.sep`, falsy segments dropped); payload keyword indexes exist for `type` and `pathSegments.0..4`.

### Decisive source
```ts
// search: one must-clause PER segment index — exact positional equality
const segments = cleanedPrefix.split("/").filter(Boolean)
filter = { must: segments.map((segment, index) => ({ key: `pathSegments.${index}`, match: { value: segment } })) }
// delete: same grammar; multiple files OR'ed via should
const filter = filters.length === 1 ? filters[0] : { should: filters }
```

**Flow:** upsert derives pathSegments from the stored RELATIVE filePath; search normalizes the prefix (`./` and `.` ⇒ no filter = whole workspace), builds positional must-clauses; deletion converts absolute paths to workspace-relative first (`path.relative(workspaceRoot, …)`), skips silently if the collection is absent, and SWALLOWS all errors after logging (:524-539). Search ALWAYS merges a `must_not type=metadata` clause so marker points never consume top-k.
**Invariant:** this is equality-per-segment, NOT prefix matching — `src/ut` matches nothing, `src/utils/file.ts` matches exactly. Deletions that swallow errors mean callers cannot distinguish "deleted" from "failed"; scanner compensates by treating cache removal as authoritative.
**Probe:** `src/services/code-index/vector-store/__tests__/qdrant-client.spec.ts` ("search" describe :1245+, "current directory path handling" :1559+); executed pins: metadata must_not :438-440, should-OR :518, swallow-log :530.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "QdrantVectorStore search directoryPrefix pathSegments filter", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the segment-equality grammar + relative-path normalization at BOTH write and delete sides (they must mirror each other or deletes miss). Adapt index depth (>4 segments deep still filters fine but loses index speedup). Omit Qdrant-specific client config. Caveat: spec covers URL parsing/init heavily; the delete-swallow branch is source-read verified only.
