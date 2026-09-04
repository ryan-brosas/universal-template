<!-- capsule-v2 -->
# Store replacement visibility — must a long-lived server see a DB swapped underneath it?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the reopen contract when the active database file is atomically replaced mid-session?

## Detect replacement, drop cached handle, serve the new generation
**Path/Symbol:** `src/mcp/mcp.c` resolve_store generation check + tests/test_mcp.c:9123 (`query_store_reopens_after_database_replacement`), 9245 (`readonly_query_does_not_mutate_db`), 9355 (`succeeds_on_readonly_fs`).
**Signature:** search_graph across a rename-replace of `<project>.db`.
**Data Shape:** GenerationA indexed and served → staged GenerationB renamed over the active path → NEXT query must return GenerationB (never stale A); read-only paths must not mutate the DB file even on read-only filesystems.

### Decisive source
```c
bool replaced = generation_b_ready && cbm_rename_replace(staged_path, active_path) == 0;
bool saw_generation_b = after && strstr(after, "GenerationB") != NULL;
bool retained_generation_a = after && strstr(after, "GenerationA") != NULL;  /* must be false */
```

**Flow:** cached store handle carries identity of the opened inode/generation → pre-query validation detects replacement → close + reopen transparently.
**Invariant:** Cached handles must never outlive the file they refer to; read-only guarantees extend to filesystem-level immutability (no journal creation attempts).
**Probe:** `tests/test_mcp.c:query_store_reopens_after_database_replacement`, `readonly_query_succeeds_on_readonly_fs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "rename_replace", limit: 5 });
```

## Verdict
Adopt handle-staleness detection for any server caching file-backed resources; adapt checks; test with real atomic renames, not mocks.
