<!-- capsule-v2 -->
# Workflow prompts — how do you teach agents your tool combinations via MCP prompts?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What do prompts/list and prompts/get return, and how is argument validation handled?

## Named workflows with typed required arguments
**Path/Symbol:** `src/mcp/mcp.c` prompts handlers + tests/test_mcp.c:1465 (`server_handle_prompts_list_workflows`), 1487 (`server_handle_prompts_get_workflows`), 1522 (`server_handle_prompts_get_validates_arguments`).
**Signature:** JSON-RPC `prompts/list` → {name, description, arguments[{name,required}]}; `prompts/get` with name+arguments → messages[].
**Data Shape:** Workflows: explore_codebase (project, question), review_change_impact (project, change, base_branch). GET renders user-role text embedding the tool SEQUENCE to run (search_graph → trace_path → get_code_snippet) with the caller's arguments interpolated; unknown/missing required args ⇒ error response.

### Decisive source
```c
ASSERT_NOT_NULL(strstr(resp, "\"name\":\"explore_codebase\""));
ASSERT_NOT_NULL(strstr(resp, "\"name\":\"review_change_impact\""));
...
/* rendered prompt embeds the tool sequence */
ASSERT_NOT_NULL(strstr(resp, "search_graph"));
ASSERT_NOT_NULL(strstr(resp, "trace_path"));
```

**Flow:** list serves catalog (no nextCursor — small set) → get validates args then renders template → agent follows the recipe.
**Invariant:** Prompt templates must reference REAL tool names (drift-guarded by tests) — a stale recipe is worse than none; validation errors must be structured.
**Probe:** the three named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "prompts_list_workflows", limit: 5 });
```

## Verdict
Adot workflow-prompt surfacing for multi-tool products; adapt recipes; keep validation strict and templates drift-guarded.
