<!-- capsule-v2 -->
# FTS rebuild fallback — how do you rebuild a full-text index when the tokenizer UDF might not exist yet?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What two-step insert guards a delete-all+repopulate against a failing split function?

## camel-split insert with raw-name fallback
**Path/Symbol:** `src/pipeline/pipeline.c:generation_rebuild_fts` (1496–1510).
**Signature:** `static int generation_rebuild_fts(cbm_store_t *store);`
**Data Shape:** Step 1: `INSERT INTO nodes_fts(nodes_fts) VALUES('delete-all')`. Step 2: repopulate `SELECT id, cbm_camel_split(name), qualified_name, label, file_path FROM nodes`. On failure of the split-form INSERT, retry with RAW names — degraded matching, never an empty index.

### Decisive source
```c
if (cbm_store_exec(store, "INSERT INTO nodes_fts(nodes_fts) VALUES('delete-all');") != CBM_STORE_OK)
    return CBM_STORE_ERR;
if (cbm_store_exec(store,
        "INSERT INTO nodes_fts(rowid, name, qualified_name, label, file_path) "
        "SELECT id, cbm_camel_split(name), qualified_name, label, file_path FROM nodes;")
    == CBM_STORE_OK) return CBM_STORE_OK;
return cbm_store_exec(store,
        "INSERT INTO nodes_fts(rowid, name, qualified_name, label, file_path) "
        "SELECT id, name, qualified_name, label, file_path FROM nodes;");
```

**Flow:** staging DB reaches publish → wipe old FTS rows → try enriched rebuild → if the UDF path errors (older DB opened by newer binary, function registration gap), fall back to verbatim names so search still works at reduced recall.
**Invariant:** The fallback must preserve rowid alignment with `nodes.id` — only the token expression changes; a failed delete-all aborts outright rather than duplicating.
**Probe:** exercised on every full publish (`tests/test_pipeline.c:2491` pins the rebuilt FTS uses `cbm_camel_split(name)`); search behavior via tests/test_mcp.c search_graph BM25 cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "generation_rebuild_fts", limit: 5 });
```

## Verdict
Adopt graceful-degradation rebuilds for UDF-dependent indexes; adapt the fallback expression; keep the explicit delete-all guard.
