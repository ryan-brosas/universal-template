<!-- capsule-v2 -->
# Node overlap lookup — how do you find "which symbols live in lines 5–8 of this file?" efficiently?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What query shape and exclusions serve line-range symbol lookups (the primitive under detect_changes seeding)?

## File+overlap SELECT excluding Module/Package containers
**Path/Symbol:** `src/store/store.c:cbm_store_find_nodes_by_file_overlap` + header store.h:437; test tests/test_store_nodes.c:788 (`store_find_by_file_overlap`, boundaries at 829/836).
**Signature:** `int cbm_store_find_nodes_by_file_overlap(s, project, file_path, start_line, end_line, cbm_node_t **out, int *count);`
**Data Shape:** Matches nodes where `file_path = ? AND start_line <= ?end AND end_line >= ?start` — standard interval-overlap predicate; EXCLUDES Module/Package structural labels; returns heap array via `cbm_store_free_nodes`.

### Decisive source
```c
/* Find nodes overlapping a line range in a file (excludes Module/Package). */
int cbm_store_find_nodes_by_file_overlap(cbm_store_t *s, const char *project, const char *file_path,
                                         int start_line, int end_line, cbm_node_t **out,
                                         int *count);
```
```c
int rc = cbm_store_find_nodes_by_file_overlap(s, "test", "main.go", 5, 8, &nodes, &count);
rc = cbm_store_find_nodes_by_file_overlap(s, "test", "main.go", 8, 15, &nodes, &count);
```

**Flow:** validate args → prepared SELECT with the four-clause overlap predicate → scan rows into growing array → finalize. Consumers: hunk-scoped impact seeds (detect_changes) and coverage probes.
**Invariant:** Container-label exclusion is semantic — File/Module spans would otherwise match every range and pollute blast-radius seeds.
**Probe:** `tests/test_store_nodes.c:store_find_by_file_overlap` plus `cbm_detect_node_in_hunks` tests in tests/test_mcp.c:7431.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_find_nodes_by_file_overlap", limit: 5 });
```

## Verdict
Adopt the closed-form interval predicate with container exclusion for any line-range symbol query; adapt label vocabulary; nothing exotic.
