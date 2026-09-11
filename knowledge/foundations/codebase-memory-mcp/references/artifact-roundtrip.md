<!-- capsule-v2 -->
# Artifact round-trip — how do you share a prebuilt graph DB with teammates safely?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the export/import contract guarantee about schema versions, sizes, and source-DB immutability?

## zstd artifact + manifest gate + VACUUM INTO best mode
**Path/Symbol:** `src/pipeline/artifact.h` (contract 1–35) + `tests/test_artifact.c` (round-trips at 165/203, guards at 146/263).
**Signature:** `int cbm_artifact_export(const char *db_path, const char *repo_path, const char *project_name, int quality);` / `int cbm_artifact_import(const char *repo_path, const char *out_db);`
**Data Shape:** Files: `.codebase-memory/graph.db.zst` + `artifact.json` (+ `.gitattributes`). Schema version = 2 (edges UNIQUE widened to include local_name_gen for #768 named-import coexistence; old binaries cannot upsert against it). Quality: FAST zstd-3 no stripping (watcher) vs BEST zstd-9 + index drop + `VACUUM INTO`.

### Decisive source
```c
/* Schema version — increment when DB schema changes ...
 * Import refuses artifacts with schema_version > current. */
#define CBM_ARTIFACT_SCHEMA_VERSION 2
...
/* BEST: Source DB should be untouched (VACUUM INTO doesn't modify source) */
ASSERT_EQ(cbm_store_count_nodes(src, "test-proj"), 2);
```

**Flow:** export → optional VACUUM INTO a stripped copy → zstd compress → write meta JSON {schema_version, original_size, commit_hash} → import verifies meta exists + version compatibility + byte size match before decompressing into the destination DB.
**Invariant:** Import must refuse on ANY of missing meta, future schema_version, or size mismatch — a partially-uploaded artifact otherwise imports silently truncated; export never mutates the source DB.
**Probe:** `tests/test_artifact.c:artifact_export_fast_roundtrip` (nodes/edges preserved), `artifact_import_rejects_size_mismatch`, `artifact_schema_version_mismatch` (version 999 ⇒ exists=false, import fails).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_artifact_export", limit: 5 });
```

## Verdict
Adopt meta-gated import with size+version checks for any shareable derived artifact; adapt compression choices; omit index-stripping if your consumers never bulk-load.
