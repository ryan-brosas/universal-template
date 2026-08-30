<!-- capsule-v2 -->
# Tool behavior annotations — how do you declare MCP tool safety metadata so agents can plan?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What annotation vocabulary does tools/list expose, and what surprising honesty is encoded there?

## read_only/destructive/idempotent/open_world per tool, test-pinned
**Path/Symbol:** `src/mcp/mcp.c` tool registry + tests/test_mcp.c:900 (`mcp_tools_have_behavior_annotations`) and 845 (`mcp_tools_help_list_matches_registry`).
**Signature:** each registry entry carries `{read_only, destructive, idempotent, open_world}` annotations surfaced in tools/list.
**Data Shape:** index_repository: read_only=false, destructive=false, idempotent=TRUE (reindex is safe to repeat). Query tools (search_graph etc.): read_only=FALSE — because resolve_store's corrupt-recovery can quarantine/delete DB files! list_projects: fully read-only. manage_adr: not idempotent.

### Decisive source
```c
/* These query tools can reach resolve_store(), whose corrupt-store
 * recovery quarantines/removes database files. Keep the annotations
 * conservative until query resolution is strictly non-mutating. */
{"search_graph", false, true, true, false},
```

**Flow:** registry → tools/list embeds annotations → agents filter/plan (e.g., never parallelize non-idempotent calls) → help text must match registry (separate drift-guard test).
**Invariant:** Annotations are CONTRACT for agent planning; the counterintuitive "queries may be destructive" entry shows the right response to a real mutation path: mark honestly, fix later.
**Probe:** `tests/test_mcp.c:mcp_tools_have_behavior_annotations`, `mcp_tools_help_list_matches_registry`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "mcp_tools_have_behavior_annotations", limit: 5 });
```

## Verdict
Adopt four-axis safety annotations with drift guards for any tool catalog; adapt axes; annotate the TRUE behavior even when embarrassing.
