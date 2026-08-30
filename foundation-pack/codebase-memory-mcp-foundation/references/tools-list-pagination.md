<!-- capsule-v2 -->
# Tools/list pagination — how do you paginate a static tool catalog for clients that cap list sizes?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What cursor semantics survive hostile cursor values while keeping the default response a single full page?

## Cursor-implies-paging with clamped offset
**Path/Symbol:** `src/mcp/mcp.c:mcp_tools_cursor_offset` (1030–1066) + `cbm_mcp_tools_list_page` (1068–1075) + nextCursor emission (903–911).
**Signature:** `static char *cbm_mcp_tools_list_page(cbm_mcp_tool_profile_t profile, const char *params_json);` — `MCP_TOOLS_PAGE_SIZE = 8`.
**Data Shape:** No cursor ⇒ ONE page containing the whole (profile-filtered) catalog, NO nextCursor. Cursor present ⇒ emit exactly 8 items starting at the parsed offset, appending `"nextCursor":"<end>"` when more remain. Unparseable/negative/over-large cursors clamp to [0, TOOL_COUNT] rather than erroring.

### Decisive source
```c
int offset = mcp_tools_cursor_offset(params_json, &has_cursor);
if (!has_cursor) {
    return cbm_mcp_tools_list_range(profile, 0, TOOL_COUNT, false);   /* single page */
}
return cbm_mcp_tools_list_range(profile, offset, MCP_TOOLS_PAGE_SIZE, true);
...
if (include_next_cursor && end < allowed_count) {
    snprintf(cursor, sizeof(cursor), "%d", end);
    yyjson_mut_obj_add_strcpy(doc, root, "nextCursor", cursor);
}
```

**Flow:** parse params → strict strtol (`endptr` consumed, errno checked, ≥0, clamp to count) → no cursor means serve-all (most clients never paginate; adding one unconditionally would break them) → with cursor, slice and append nextCursor only if a remainder exists.
**Invariant:** nextCursor must be ABSENT on the final page (tests assert NULL); the same tool name appearing twice in params must not confuse paging — dedup happens upstream of slicing.
**Probe:** `tests/test_mcp.c:server_handle_tools_list_defaults_to_all_tools_and_accepts_cursor` (default: no nextCursor + mutators present per profile; cursor:"8" slices).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "mcp_tools_cursor_offset", limit: 5 });
```

## Verdict
Adopt lazy pagination (cursor-in ⇒ pages out; absent ⇒ everything) for MCP-compatible catalogs; adapt page size; omit profile filtering here if your tiers are separate servers.
