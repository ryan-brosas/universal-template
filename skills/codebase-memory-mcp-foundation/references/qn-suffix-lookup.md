<!-- capsule-v2 -->
# QN suffix lookup — how do you find a symbol by the tail of its qualified name without false positives?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does "ends with .suffix" avoid matching `helper.parse` when you searched for `rser.parse`?

## Dot-boundary LIKE + exact-equality OR
**Path/Symbol:** `src/store/store.c:cbm_store_find_nodes_by_qn_suffix` (3370–3414).
**Signature:** `int cbm_store_find_nodes_by_qn_suffix(cbm_store_t *s, const char *project, const char *suffix, cbm_node_t **out, int *count);`
**Data Shape:** Pattern = `"%.<suffix>"` OR exact equality with suffix; optional project binding (?1) keeps the query project-scoped; used by get_code_snippet's fallback resolution (mcp.c:8806).

### Decisive source
```c
/* Match QNs ending with ".suffix" or exactly equal to suffix */
char like_pattern[CBM_SZ_512];
snprintf(like_pattern, sizeof(like_pattern), "%%.%s", suffix);
const char *sql_with_project =
    "SELECT ... FROM nodes WHERE project = ?1 AND (qualified_name LIKE ?2 OR qualified_name = ?3)";
```

**Flow:** build dotted-suffix pattern → prepare (project-scoped variant when project given) → scan into growable array → free via store_free_nodes.
**Invariant:** The leading `%.` (dot REQUIRED) is what makes suffix search segment-aware — without it every longer name ending in the same characters matches.
**Probe:** exercised by snippet resolution tests in tests/test_mcp.c (`tool_get_code_snippet_*`) and direct node tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_find_nodes_by_qn_suffix", limit: 5 });
```

## Verdict
Adopt dot-anchored suffix patterns for hierarchical-name lookup; adapt separator; pair with an exact-match arm for top-level names.
