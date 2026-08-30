<!-- capsule-v2 -->
# Depth clamping — how do you handle a caller requesting max_depth 1000 on an 18-deep chain?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the clamp policy for traversal depth arguments?

## Server-side clamp to a sane maximum
**Path/Symbol:** `src/mcp/mcp.c` trace handler + tests/test_mcp.c:3448 (`tool_trace_call_path_depth_clamped`).
**Signature:** trace_path args.max_depth → clamped internally before BFS.
**Data Shape:** Fixture: linear chain n00→…→n17 (18 nodes, 17 CALLS edges). Oversized depth request is clamped (not rejected) and the full reachable chain returns; negative/zero handled by defaults.

### Decisive source
```c
/* Linear call chain n00 -CALLS-> n01 -> ... -> n17 (18 nodes). */
TEST(tool_trace_call_path_depth_clamped) { ... }
```

**Flow:** parse int arg → clamp to [default?, MAX_DEPTH] → traverse.
**Invariant:** Clamp rather than error for over-asks (the caller wants "as deep as needed"); error only for nonsense types. Document the effective ceiling in tool help.
**Probe:** `tests/test_mcp.c:tool_trace_call_path_depth_clamped`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "max_depth", limit: 5 });
```

## Verdict
Adopt clamp-don't-reject for bounded-resource args; adapt ceilings; pair with node budgets from the BFS capsule.
