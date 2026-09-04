<!-- capsule-v2 -->
# Replicate upload-first — how do you create N document copies with zero half-created rows?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What write order makes multi-copy document replication survive partial failure without ever showing a "ready" library row whose bytes or version are missing?

## Client-side UUIDs → parallel uploads → bulk inserts → compensating deletes
**Path/Symbol:** `backend/src/lib/chat/tools/toolDispatcher.ts:1510-1862` (`replicate_document` branch); key sites :1620 (pre-generated ids comment), :1652 (`Promise.all(uploadJobs)`), :1704-1713 (documents rollback), :1759-1764 (broken-copy delete). Direct tests: `src/lib/__tests__/workflowAssetReplication.test.ts` + `src/lib/__tests__/audit.test.ts` (event fan-out).
**Signature:** branch of `runToolCalls`; args `{doc_id, new_filename?, count? 1..20}`; emits doc_replicate_start → doc_replicated events.
**Data Shape:** per-copy pre-claimed `crypto.randomUUID()` id; uploads = doc bytes (+ PDF rendition when source has/needs one) in ONE parallel batch; rows inserted documents→document_versions→per-row current_version_id UPDATE fan-out.

### Decisive source
```ts
// Pre-generate the document ids client-side (mirrors persistGeneratedFile) so
// every copy's bytes can be uploaded BEFORE any documents row exists: a failure
// mid-flight then leaves orphaned STORAGE OBJECTS, never a user-visible "ready"
// library row without content.
…
if (verErr || !insertedVersions || insertedVersions.length !== newDocs.length) {
    // Roll the documents rows back so no version-less "ready" rows stay visible
    await db.from("documents").delete().in("id", newDocs.map(d => d.id));
}
```

**Flow:** resolve source (active version bytes pulled ONCE for all copies) → build N filenames (count=1 keeps "(copy)"/requested name; count>1 uses " (n)" suffixing) → upload all bytes+renditions in parallel → bulk insert N document rows (status ready) → bulk insert N version rows (size/hash computed from the SAME raw buffer: `size_bytes: raw.byteLength` beside `content_sha256(raw)` so a verifier can never see size disagree with hash) → per-row current_version_id updates checked IN-BAND (Supabase builders report via `error`, never reject) → copies that failed linking are DELETED and reported in `failed_copies`, not silently dropped from an ok:true payload.
**Invariant:** Storage-before-metadata ordering everywhere; every in-band error checked (`.error` fields, not try/catch); count mismatches between requested inserts and returned rows treated as failure even when error is null. Orphaned storage objects on late failure are acceptable garbage; visible broken rows are not.
**Probe:** `grep -c 'orphaned storage objects' src/lib/chat/tools/toolDispatcher.ts` → 1; `grep -c 'failed_copies' src/lib/chat/tools/toolDispatcher.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "replicate_document uploadFile storageKey current_version_id", limit: 10 });
```

## Verdict
Adopt upload-before-insert + client-claimed ids + compensating deletes + in-band result checking as portable durability contracts; adapt table names and rendition logic; omit Office→PDF conversion specifics.
