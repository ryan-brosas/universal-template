<!-- capsule-v2 -->
# Store restore — how do you copy one store's contents into another (the migration primitive)?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does restore_from guarantee about id preservation and completeness?

## ATTACH-based copy preserving rowids
**Path/Symbol:** `src/store/store.c:cbm_store_restore_from` + tests/test_store_nodes.c:1143 (`store_restore_from`).
**Signature:** `int cbm_store_restore_from(cbm_store_t *dst, cbm_store_t *src);`
**Data Shape:** Copies ALL rows from src into dst keeping rowids (Func5 findable by same QN, count exactly 10); implemented via SQL-level copy (ATTACH or backup API) rather than per-row C loops.

### Decisive source
```c
/* Restore: copy from src → dst */
int rc = cbm_store_restore_from(dst, src);
ASSERT_EQ(rc, CBM_STORE_OK);
rc = cbm_store_find_node_by_qn(dst, "test", "test.main.Func5", &found);
ASSERT_STR_EQ(found.name, "Func5");
int cnt = cbm_store_count_nodes(dst, "test");
ASSERT_EQ(cnt, 10);
```

**Flow:** begin on dst → copy tables in FK-safe order (projects, nodes, edges, hashes…) → commit. Used by repair/rebuild paths that stage a fresh DB then swap.
**Invariant:** Rowid preservation matters because external references (FTS rowid alignment) assume node ids are stable across the operation.
**Probe:** `tests/test_store_nodes.c:store_restore_from`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_restore_from", limit: 5 });
```

## Verdict
Adopt SQL-level store copies with id stability for rebuild pipelines; adapt table order; verify with count+spot-check reads like the test does.
