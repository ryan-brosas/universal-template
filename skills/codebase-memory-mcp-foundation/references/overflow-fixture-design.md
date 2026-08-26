<!-- capsule-v2 -->
# Overflow fixture design — how do you test a bounds-check path that stub data can't reach?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What makes the #235 overflow fixture exercise REAL bounds checks instead of passing vacuously?

## Real DBs with long INTERNAL names, 40 of them
**Path/Symbol:** tests/test_mcp.c:8659 (`tool_bad_project_name_no_overflow_issue235`), 8742 (`tool_bad_project_error_valid_json_issue235`).
**Signature:** fixture builds 40 valid stores whose internal project names exceed ~120 chars each.
**Data Shape:** collect_db_project_names advertises each db's INTERNAL name (#704) — so stub files would skip the accumulation loop entirely. 40 × ~120 chars > 4KB buffer ⇒ bounds path genuinely runs; response stays valid JSON with "not found".

### Decisive source
```c
/* 40 * ~120-char names overflows the 4 KB available-projects buffer.
 * collect_db_project_names advertises each db's INTERNAL project name
 * (#704), so the fixture must hold valid dbs with long internal names —
 * not stub files — for the bounds-check path to actually be exercised. */
enum { ISSUE235_N = 40 };
```

**Flow:** create real DBs with long names → request a nonexistent project (forces candidate enumeration) → assert clean error + valid JSON.
**Invariant:** Fixtures must satisfy every precondition of the code path under test — an overflow test with empty inputs proves nothing about the overflow.
**Probe:** `tests/test_mcp.c:tool_bad_project_name_no_overflow_issue235`, `tool_bad_project_error_valid_json_issue235`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "collect_db_project_names", limit: 5 });
```

## Verdict
Adopt precondition-satisfying fixtures for security/bounds tests; adapt counts; pair with JSON-validity assertions on error paths.
