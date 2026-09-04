<!-- capsule-v2 -->
# Dimension-mismatch collection recreation — what happens when the configured embedding size no longer matches the live Qdrant collection?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How is a vector-size mismatch repaired, and which failure stages are distinguished?

## Delete → verify-gone → recreate, with staged error context
**Path/Symbol:** `src/services/code-index/vector-store/qdrant-client.ts:initialize/_recreateCollectionWithNewDimension` (:149-215; :222-293).
**Signature:** `initialize(): Promise<boolean>` (true = created/recreated); existing size read from `config.params.vectors` (number or named-vectors `{size}`).
**Data Shape:** three failure stages — deletion failed / deleted-but-verification-saw-it-still-there / recreate failed — each wrapped in a `vectorDimensionMismatch` Error carrying `.cause`.

### Decisive source
```ts
await this.client.deleteCollection(this.collectionName)
await new Promise((resolve) => setTimeout(resolve, 100))
const verificationInfo = await this.getCollectionInfo()
if (verificationInfo !== null) { throw new Error("Collection still exists after deletion attempt") }
```

**Flow:** initialize: missing ⇒ create (`vectors.size`, Cosine, on_disk; hnsw m=64 ef_construct=512 on_disk) + payload indexes (`type`, `pathSegments.0..4`, "already exists" tolerated); exists-with-matching-size ⇒ false; mismatch ⇒ recreate ladder. The 100ms sleep + null-check is a distributed-state guard against eventual-consistent deletes. Errors with a `.cause` are re-thrown AS-IS by initialize so the staged context survives one wrap at most.
**Invariant:** recreation is destructive-by-design (all vectors die) but the marker protocol makes the NEXT start a clean full reindex; never silently keep a mismatched collection — every subsequent upsert would fail per-point.
**Probe:** `src/services/code-index/vector-store/__tests__/qdrant-client.spec.ts` ("should recreate collection if it exists but vectorSize mismatches" :592, "2048 to 768 dimensions" :897, "verify collection deletion before proceeding" :816, "still exists after deletion attempt" :850).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "_recreateCollectionWithNewDimension vectorDimensionMismatch createPayloadIndexes", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt verify-after-delete before recreate and staged error causes. Adapt HNSW/payload-index set. Omit URL-parse fallbacks (covered by the store's spec suite).
