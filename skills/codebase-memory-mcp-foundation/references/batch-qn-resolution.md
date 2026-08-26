<!-- capsule-v2 -->
# Batch QN resolution — how do you resolve 500 qualified names without 500 round-trips?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the batch-lookup contract including the missing-name sentinel?

## One prepared statement + 0-for-missing convention
**Path/Symbol:** `src/store/store.c:cbm_store_find_node_ids_by_qns` + tests/test_store_nodes.c:1199 (`store_find_node_ids_by_qns`).
**Signature:** `int cbm_store_find_node_ids_by_qns(cbm_store_t *s, const char *project, const char *const *qns, int count, int64_t *ids_out);`
**Data Shape:** ids_out[i] = rowid or 0 when absent; empty/NULL batch ⇒ found=0 OK. Registry resolution ladder consumes this to map callee names in one pass.

### Decisive source
```c
/* Batch lookup: 2 found + 1 missing */
const char *qns[] = {"test.A", "test.B", "test.missing"};
int64_t ids[3];
int found = cbm_store_find_node_ids_by_qns(s, "test", qns, 3, ids);
ASSERT_EQ(found, 2);
ASSERT_EQ(ids[2], 0); /* missing → 0 */
```

**Flow:** prepare once → bind+step per QN writing rowid-or-0 → finalize → return hit count.
**Invariant:** 0-as-missing works because SQLite rowids start at 1 — document it; never return partial arrays without the count.
**Probe:** the named test plus registry-ladder consumers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_find_node_ids_by_qns", limit: 5 });
```

## Verdict
Adopt prepared batch lookups with explicit missing sentinels; adapt sentinel; pair with resolution confidence layers for ambiguity handling.
