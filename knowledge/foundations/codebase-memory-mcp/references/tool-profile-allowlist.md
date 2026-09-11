<!-- capsule-v2 -->
# Tool profiles — how do you expose a read-only agent surface without duplicating tool catalogs?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you restrict one MCP server to analysis/scout tool tiers, and what must happen to mutators and HTTP?

## Allowlist tiers + fail-closed argument handling
**Path/Symbol:** `src/mcp/mcp.c:mcp_tool_allowed` (780–812) + profile parsing (818–830) + suites tests/test_mcp.c:1346/1384/1429.
**Signature:** `static bool mcp_tool_allowed(cbm_mcp_tool_profile_t profile, const char *name);` — set once via `--tool-profile=analysis|scout`.
**Data Shape:** ALL (default) = everything. ANALYSIS = 11 tools: search_graph, query_graph, trace_path, get_code_snippet, get_graph_schema, get_architecture, search_code, list_projects, index_status, check_index_coverage, detect_changes. SCOUT = 7: search_graph, trace_path, get_code_snippet, get_architecture, list_projects, index_status, check_index_coverage.

### Decisive source
```c
if (!name) return false;
if (profile == CBM_MCP_TOOL_PROFILE_ALL) return true;
...
for (size_t i = 0U; i < allowed_count; i++) {
    if (strcmp(name, allowed[i]) == 0) return true;
}
return false;
```

**Flow:** argv parse sets the process-level profile → initialize response advertises only the filtered catalog → tools/list paginates within the tier → any tools/call for a non-member name fails closed with an explicit error; HTTP exposure follows the same gate (`cbm_mcp_tool_profile_allows_http`) so restricted profiles also disable web access; malformed/unknown profile values are hard errors, not silent fallback to ALL.
**Invariant:** The allowlist is data (const arrays) — adding tools never leaks into restricted tiers by accident; unknown profile ⇒ refuse startup.
**Probe:** `tests/test_mcp.c:server_handle_analysis_profile_filters_and_rejects_mutators`, `server_handle_scout_profile_exposes_only_the_fast_tier`, `analysis_profile_arguments_fail_closed_and_disable_http`; CLI twin: `tests/test_cli.c:cli_read_only_agents_do_not_receive_mutating_mcp_server`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "mcp_tool_allowed", limit: 5 });
```

## Verdict
Adopt static allowlist tiers with fail-closed parsing for capability-restricted agents; adapt membership lists; omit per-dialect renderer variants if you serve only MCP clients.
