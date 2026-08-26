<!-- capsule-v2 -->
# URL-path edge lookup — how do you find which HTTP edges reference a route path?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How are edge properties queried (JSON-in-column) without a property table?

## properties_json LIKE scan scoped to HTTP_CALLS
**Path/Symbol:** `src/store/store.c:cbm_store_find_edges_by_url_path` + tests/test_store_nodes.c:1102 (`store_find_edges_by_url_path`).
**Signature:** `int cbm_store_find_edges_by_url_path(cbm_store_t *s, const char *project, const char *needle, cbm_edge_t **out, int *count);`
**Data Shape:** Edges carry `properties_json` blobs like `{"url_path":"/api/orders/create","confidence":0.8}`; lookup = substring needle ("orders") against url_path within the project; no match ⇒ OK with count 0.

### Decisive source
```c
/* Search for edges containing "orders" */
rc = cbm_store_find_edges_by_url_path(s, "test", "orders", &edges, &count);
ASSERT_EQ(count, 1);
...
rc = cbm_store_find_edges_by_url_path(s, "test", "users", &edges, &count);
ASSERT_EQ(count, 0);
```

**Flow:** build LIKE arm over properties_json filtered to HTTP_CALLS-type rows → scan into heap array → free via store_free_edges.
**Invariant:** JSON-in-column is acceptable for low-cardinality query patterns only — anything hotter needs generated columns or a real table; substring semantics documented like file_pattern (#200).
**Probe:** `tests/test_store_nodes.c:store_find_edges_by_url_path`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_find_edges_by_url_path", limit: 5 });
```

## Verdict
Adopt JSON-blob columns only with measured query patterns; adapt to JSON1 functions if hot; keep count-0-is-OK contracts.
