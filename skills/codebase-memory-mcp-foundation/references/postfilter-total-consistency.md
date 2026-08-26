<!-- capsule-v2 -->
# Trace test-filter totals — why must "include_tests:false" change the TOTAL, not just the items?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the consistency contract between a filtered result set and its reported total?

## Filter applied before counting; subtree-root variant pinned (#1294)
**Path/Symbol:** `src/mcp/mcp.c` trace handler + tests/test_mcp.c:1743 (`tool_trace_totals_respect_test_filter`), 1814 (`tool_trace_totals_respect_test_filter_tests_root_subtree_issue1294`).
**Signature:** trace_path with include_tests=false over CALLS edges.
**Data Shape:** Fixture: prod_caller→tgt and test_caller→tgt (tests/test_x.c). Filtered trace: total EXCLUDES the test-originated path; variant pins behavior when the traced ROOT itself lives under tests/.

### Decisive source
```c
cbm_edge_t e1 = {... .source_id = pid, .target_id = tid, .type = "CALLS"};
cbm_edge_t e2 = {... .source_id = xid, .target_id = tid, .type = "CALLS"};
```
```c
TEST(tool_trace_totals_respect_test_filter_tests_root_subtree_issue1294) { ... }
```

**Flow:** resolve target → traverse inbound → classify each contributing node by testness (path convention) → filter → count AFTER filtering so total == len(items) semantics hold for agents doing arithmetic.
**Invariant:** Never report pre-filter totals alongside filtered pages — agents reconcile counts against items and lose trust on mismatch.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "trace", limit: 5 });
```

## Verdict
Adopt post-filter counting everywhere you expose both totals and lists; adapt test-detection to your conventions; pin root-in-subtree edge cases explicitly.
