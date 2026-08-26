<!-- capsule-v2 -->
# Dependent-files closure — which files must re-resolve when these files change?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How is the reverse dependency set computed, and what noise classes are excluded?

## CALLS-based reverse lookup minus self-reference and container noise
**Path/Symbol:** `src/store/store.c:cbm_store_get_dependent_files` (3928+) + tests/test_store_nodes.c:609 (`store_dependent_files_lookup`).
**Signature:** `int cbm_store_get_dependent_files(cbm_store_t *s, const char *project, const char **files, int count, cbm_string_list_t *out);`
**Data Shape:** For seed set {b.py} with a→b, c→b, b→b edges: result EXACTLY {a.py, c.py} — self-references are not dependents; Folder nodes with CONTAINS_FILE edges never surface (placeholder file_path "{}" can't be re-resolved).

### Decisive source
```c
/* a.py and c.py each call into b.py; b.py also references itself ... Dependents
 * of {b.py} must be exactly {a.py, c.py}: the self-reference is not a dependent,
 * d.py is unrelated. */
/* Structural container noise: a Folder node (placeholder file_path) with a
 * CONTAINS_FILE edge into b.py must never surface as a dependent */
```

**Flow:** map seed files → their node ids → SELECT DISTINCT source-side file_path over inbound CALLS → filter out seeds themselves and non-file labels → return list consumed by closure_try_plan's consumer invalidation.
**Invariant:** Only REAL source files qualify — placeholder paths from structural containers would poison incremental replans with unresolvable entries.
**Probe:** `tests/test_store_nodes.c:store_dependent_files_lookup`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_dependent_files", limit: 5 });
```

## Verdict
Adopt filtered reverse-dependency queries for incremental invalidation; adapt exclusions to your node taxonomy; test self-reference explicitly.
