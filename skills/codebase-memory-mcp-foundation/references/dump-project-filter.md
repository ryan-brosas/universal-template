<!-- capsule-v2 -->
# Dump to file — how do you export a project's graph for backup or cross-machine move?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does store_dump write and what does the import side verify?

## SQL dump with project filter
**Path/Symbol:** `src/store/store.c:cbm_store_dump_to_file` + tests/test_store_search.c:677 (`store_dump_to_file`) + dump-verify floors capsule.
**Signature:** `int cbm_store_dump_to_file(cbm_store_t *s, const char *project, const char *out_path);`
**Data Shape:** Emits portable SQL (schema + rows for the chosen project, or all) to out_path; import path re-executes under transaction; verification uses floor/ratio rules rather than byte equality.

### Decisive source
```c
TEST(store_dump_to_file) { ... }
```

**Flow:** open output → write schema DDL → stream INSERT batches per table filtered by project → fsync → close. Companion artifact export (zstd + manifest) covers the share-with-teammates case.
**Invariant:** Project-filtered dumps must keep rowid/foreign-key coherence — either dump whole tables or remap ids; partial tables without remap corrupt on import.
**Probe:** `tests/test_store_search.c:store_dump_to_file`; verify-side in tests/test_dump_verify.c.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_dump", limit: 5 });
```

## Verdict
Adopt filtered SQL dumps with explicit id-coherence rules; adapt format; pair with count-floor verification on import.
