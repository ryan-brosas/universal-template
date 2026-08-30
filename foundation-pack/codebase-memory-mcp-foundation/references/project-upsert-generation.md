<!-- capsule-v2 -->
# Project CRUD upsert — what does "re-index the same project" mean at the projects-table level?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does re-indexing refresh indexed_at and trigger generation bumps without duplicating rows?

## ON CONFLICT(project) UPDATE + store_meta bump side-effect
**Path/Symbol:** `src/store/store.c:cbm_store_upsert_project` (1600s region) + tests/test_store_nodes.c:112 (`store_project_crud`), 147 (`store_project_update`).
**Signature:** `int cbm_store_upsert_project(cbm_store_t *s, const char *name, const char *root_path);`
**Data Shape:** Upsert keyed by project name; on conflict updates root_path + indexed_at (ISO 8601 now); the SAME call is the choke point that bumps `mutation_gen` in store_meta (see generation-cursor capsule). Table constrained to effectively-one primary row per DB (shadow `::missed` rows exempt).

### Decisive source
```c
"(project, generation, index_mode, recorded_at, recording_status, "
...
"ON CONFLICT(project) DO UPDATE SET generation=?2, index_mode=?3, ..."
```
```c
TEST(store_project_update) { ... }
```

**Flow:** insert-or-update row → seed/bump store_meta → every index run (full/incremental/watcher) passes through here making it the natural mutation counter.
**Invariant:** Reindex must be idempotent at the row level while still advancing generation; integrity checks rely on the single-primary-row invariant (count >1 ⇒ CORRUPT).
**Probe:** `tests/test_store_nodes.c:store_project_crud`, `store_project_update`, plus verdict corruption test seeding a bogus second row.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_upsert_project", limit: 5 });
```

## Verdict
Adopt upsert-with-side-counter for identity rows that need change detection; adapt meta table; keep the shallow-integrity coupling to row count.
