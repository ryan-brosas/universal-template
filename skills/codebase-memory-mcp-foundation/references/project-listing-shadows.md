<!-- capsule-v2 -->
# list_projects — how do you enumerate indexed projects without leaking internal shadow rows?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the project listing include, and why do `::missed` rows stay hidden?

## Primary-rows-only listing with per-project stats
**Path/Symbol:** `src/store/store.c:cbm_store_list_projects` (~7700s) + shadow-row semantics in pass_cross_repo.c:123–152; tests/test_store_arch.c:503+.
**Signature:** `int cbm_store_list_projects(cbm_store_t *s, cbm_project_info_t **out, int *count);`
**Data Shape:** One row per PRIMARY project (name, root_path, indexed_at, node/edge counts). Shadow `<name>::missed` rows (cross-repo scan bookkeeping) are excluded from user-facing listings but still count toward identity checks internally.

### Decisive source
```c
TEST(store_list_projects) { ... }
/* cross-repo: only shadow rows stop counting toward [single-primary];
 * this is the same defect mcp.c fixed for list_projects in #1044. */
```

**Flow:** SELECT from projects WHERE name NOT LIKE '%::missed%' → attach stats → emit. The #1044 fix established the convention that BOTH the tool layer AND store-level single-primary checks ignore shadows consistently.
**Invariant:** Shadow-row handling must be consistent across every consumer or identity validation (cr_store_has_exact_project) diverges from what users see.
**Probe:** `tests/test_cross_repo.c:cross_repo_accepts_project_with_missed_shadow_row_issue1609` pins the store side.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_list_projects", limit: 5 });
```

## Verdict
Adopt explicit shadow/internal-row conventions with a single filtering predicate reused everywhere; adapt naming scheme; test both surfaces together.
