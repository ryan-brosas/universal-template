<!-- capsule-v2 -->
# LSP surface codec — what makes a body edit different from a signature edit for dependents?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you persist a per-file "exported surface" so byte equality of the serialization IS surface equality?

## Canonical bytes + sha early cutoff
**Path/Symbol:** `src/pipeline/lsp_surface.c:cbm_lsp_surface_build_rows` (129–179) with header contract (1–32).
**Signature:** `int cbm_lsp_surface_build_rows(const char *project, CBMFileResult **cache, int file_count, ..., cbm_lsp_surface_row_t **out_rows, int *out_count);`
**Data Shape:** One row per file: {rel_path, surface_sha = sha256(defs_json), defs_json = canonical JSON array of the file's LSP defs, ref_bloom blob, config_ctx}. Empty surfaces still get a row ("no defs" must hash too). Codec version stamped; rows from other versions fail closed.

### Decisive source
```c
/*  1. ROUND-TRIP FIDELITY: defs_from_json(build_json(defs)) must hand the
 *     per-language registrars the same values collect_all_defs would have
 *     built from a real parse ...
 *  2. CANONICAL BYTES: every field is written, in fixed order, with an
 *     explicit JSON null for absent strings (NULL and "" are DIFFERENT values
 *     in the CBMLSPDef contract ...). Byte equality of the serialization
 *     therefore IS surface equality, and the sha over the bytes is the
 *     early-cutoff key: a body edit reserializes identically. */
```

**Flow:** extraction collects defs per file → codec serializes each def's fields in fixed order (explicit nulls, reg-only labels like Field/Table/View included so renames can't slip past) → sha256 stored → incremental planner compares old vs freshly-probed sha: equal ⇒ body edit, skip dependents; changed ⇒ check for ADDED names before seeding dependent re-resolution.
**Invariant:** NULL and "" are semantically distinct in the def contract — collapsing them silently degrades cross-file resolution only on the incremental path, exactly the divergence class this exists to kill.
**Probe:** `tests/test_pipeline.c:pipeline_lsp_surface_persisted_and_body_edit_invariant` (body edit keeps sha; adding param changes it) and `tests/test_store_nodes.c:store_lsp_surface_round_trip` (batch upsert incl. bloom-with-NUL, empty-surface row, replace-on-conflict).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_lsp_surface_build_rows", limit: 5 });
```

## Verdict
Adopt canonical-bytes hashing with explicit-null field discipline; adapt the def-field list to your language servers; omit the bloom-filter column if your dependent query doesn't need candidate prefiltering.
