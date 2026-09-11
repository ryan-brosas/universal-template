<!-- capsule-v2 -->
# Trace-path exactly-once pagination — how do you page through a traversal without repeats or gaps?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What contract makes offset-paged trace results safe for an agent walking a call chain?

## Deterministic order + visited-set dedup + total accounting
**Path/Symbol:** tests/test_mcp.c:3101 (`tool_trace_path_pages_exactly_once`).
**Signature:** MCP tool `trace_path` with offset/limit paging over BFS rows.
**Data Shape:** Concatenating all pages yields each reachable node exactly once; per-page items carry stable ids so an agent can detect overlap; totals consistent across pages.

### Decisive source
```c
TEST(tool_trace_path_pages_exactly_once) { ... }
```

**Flow:** full traversal computed once (BFS from origin, deterministic neighbor order) → slice by offset/limit → emit with total count → repeated pages with same params return identical slices.
**Invariant:** Never re-traverse per page — compute-then-slice is what makes "exactly once" hold under concurrent writes within one generation.
**Probe:** the named test plus generation-mismatch twins at tests/test_mcp.c:2785–2830.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "trace_path", limit: 5 });
```

## Verdict
Adopt compute-then-slice for paginated traversals; adapt limits; pair with generation cursors for staleness detection.
