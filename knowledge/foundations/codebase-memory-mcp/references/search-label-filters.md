<!-- capsule-v2 -->
# Search label filters — how do you exclude noise labels (Route, Module) from symbol search?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the SQL shape for label exclusion, and how does the schema tool know which labels exist?

## NOT IN dynamic list + schema introspection
**Path/Symbol:** `src/store/store.c:cbm_store_get_schema` (store.h:653) + search exclusion arm; tests/test_store_search.c:592 (`store_schema_info`, 613+ `store_search_exclude_labels`).
**Signature:** `int cbm_store_get_schema(cbm_store_t *s, const char *project, cbm_schema_info_t *out);` / params->exclude_labels in cbm_store_search.
**Data Shape:** Schema returns DISTINCT node_label/edge_type sets with counts (≥2 labels incl. Function in fixture; ≥1 edge type CALLS). Exclusion: `label NOT IN (?,?,...)` built dynamically with one placeholder per excluded label.

### Decisive source
```c
TEST(store_schema_info) {
    ...
    ASSERT_GTE(schema.node_label_count, 2);
    ASSERT_GTE(schema.edge_type_count, 1);
```
```c
/* Create nodes with different labels ... Function / Route / Method */
rc = cbm_store_search(... .exclude_labels = {"Route"}, ...);
```

**Flow:** schema: grouped SELECTs over nodes/edges → free via cbm_store_schema_free. Search: append parameterized NOT IN arm before LIKE arms → planner still uses idx_nodes_name for remaining predicates.
**Invariant:** Dynamic IN-lists need exact placeholder counts — a mismatch is an SQLITE_MISUSE bug class; exclusion applies BEFORE ranking so scores aren't diluted.
**Probe:** `tests/test_store_search.c:store_schema_info`, `store_search_exclude_labels`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_schema", limit: 5 });
```

## Verdict
Adopt parameterized label exclusion + runtime schema introspection; adapt defaults; keep schema counts as a completeness signal.
