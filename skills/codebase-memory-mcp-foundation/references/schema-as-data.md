<!-- capsule-v2 -->
# get_graph_schema — how do you expose your node/edge vocabulary to agents at runtime?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Why serve the schema as data, and what must it include?

## Self-describing catalog: labels, edge types, properties
**Path/Symbol:** `src/store/store.c:cbm_store_get_schema` (~7500s) + tests/test_store_arch.c:421–460 (`store_get_graph_schema`, 461+ `get_graph_schema_lists_all_edge_types`).
**Signature:** `int cbm_store_get_schema(cbm_store_t *s, const char *project, cbm_graph_schema_t **out);`
**Data Shape:** Enumerates every node label (Function, Method, Module, File, Route, Resource, …), every edge type (CALLS, DEFINES, IMPORTS, USAGE, HANDLES, TESTS, SIMILAR_TO, SEMANTICALLY_RELATED, CROSS_HTTP_CALLS, FILE_CHANGES_WITH, …), and per-type property names — the contract query_graph/trace_path callers rely on.

### Decisive source
```c
TEST(store_get_graph_schema) { ... }
TEST(get_graph_schema_lists_all_edge_types) { ... }   /* completeness pinned */
```

**Flow:** static vocabulary tables + live counts from the store → emit; new passes adding edge types MUST extend this table (the completeness test fails otherwise).
**Invariant:** Schema-as-data keeps agents from hard-coding vocabularies that drift between index versions.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_schema", limit: 5 });
```

## Verdict
Adopt self-describing catalogs with a completeness test for any graph API; adapt vocabulary; treat schema drift as a release-note event.
