<!-- capsule-v2 -->
# Project-name tail resolution — how do you let agents type "suffix1025" instead of the full project name?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the tail-matching rule for project arguments, and when must it refuse?

## Unique-suffix resolution with ambiguity refusal
**Path/Symbol:** `src/mcp/mcp.c` project-arg resolution + tests/test_mcp.c:4015 (`tool_project_arg_resolves_unique_tail_issue1025`), 3914/3958 (name-alias twins issue640).
**Signature:** resolve_store accepts either an exact project name OR a unique suffix; alias via index_repository `name` param also supported.
**Data Shape:** Fixture: projects `E-project-graph-suffix1025`, `F-alpha-amb1025`, `G-beta-amb1025`. Querying `"suffix1025"` resolves uniquely (issue #1025 was RED); querying `"amb1025"` matches TWO ⇒ ambiguous error, never a silent pick.

### Decisive source
```c
/* 1. Unique tail resolves (RED today: "project not found"). */
r = cbm_mcp_handle_tool(srv, "search_graph",
                        "{\"project\":\"suffix1025\",\"name_pattern\":\".*target.*\"}");
```

**Flow:** exact match? → done. Else scan cache-dir DBs' internal names for suffix matches → exactly one ⇒ adopt → multiple ⇒ explicit ambiguity listing candidates.
**Invariant:** Ambiguity must fail loudly with candidates — silently choosing by id order makes agent results unreproducible across runs.
**Probe:** `tests/test_mcp.c:tool_project_arg_resolves_unique_tail_issue1025` plus the issue640 alias pair.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "unique_tail", limit: 5 });
```

## Verdict
Adopt unique-tail convenience resolution for any named-resource API; adapt minimum length; always enumerate on ambiguity.
