<!-- capsule-v2 -->
# Node upsert dedup — why is (project, qualified_name) the identity, and what must cascade?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do repeated indexes avoid node duplication, and what happens on delete_project?

## ON CONFLICT(project,qn) UPDATE + FK cascade
**Path/Symbol:** `src/store/store.c:cbm_store_upsert_node` + tests/test_store_nodes.c:187 (`store_node_crud`), 239 (`store_node_dedup`), 466 (`store_cascade_delete`).
**Signature:** `int64_t cbm_store_upsert_node(cbm_store_t *s, const cbm_node_t *n);`
**Data Shape:** Unique index on (project, qualified_name); re-upsert updates label/name/properties (later write wins — `{"updated":true}` visible after double-insert with count still 1); edges carry FKs to nodes so project delete cascades nodes AND edges to zero.

### Decisive source
```c
/* Insert same QN twice — should update, not duplicate */
cbm_store_upsert_node(s, &n1);
cbm_store_upsert_node(s, &n2);
int cnt = cbm_store_count_nodes(s, "test");
ASSERT_EQ(cnt, 1);
...
/* Delete project — should cascade */
cbm_store_delete_project(s, "test");
ASSERT_EQ(ncnt, 0);
ASSERT_EQ(ecnt, 0);
```

**Flow:** upsert returns rowid (existing OR new — callers may build edges immediately) → batch variant for bulk loads → deletes go through project-level cascade.
**Invariant:** Identity is the QUALIFIED NAME within a project, never the name or path; any new node kind must respect this or incremental merges will fork entities.
**Probe:** `tests/test_store_nodes.c:store_node_dedup`, `store_node_batch_upsert`, `store_cascade_delete`, `store_find_by_qn_suffix_dot_boundary`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_upsert_node", limit: 5 });
```

## Verdict
Adopt QN-identity upserts with FK cascades for graph stores; adapt key columns; test the dot-boundary suffix cases while you're there.
