<!-- capsule-v2 -->
# Snippet context-bomb guard — how do you serve code snippets to agents without one call returning 400KB?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How should a get-snippet tool cap structural nodes while still telling the agent how to get the rest?

## 500-line clip + source_clipped flag
**Path/Symbol:** `src/mcp/mcp.c:build_snippet_response` (8638–8700) with `MCP_SNIPPET_MAX_LINES = 500` (line 31).
**Signature:** `static char *build_snippet_response(cbm_mcp_server_t *srv, cbm_node_t *node, const char *match_method, bool include_neighbors, cbm_node_t *alternatives, int alt_count);`
**Data Shape:** Response JSON adds `"source_clipped":true` and `"clipped_at_lines":500` when the requested span exceeded the cap; exact original range remains in start_line/end_line for a targeted re-read; source is sanitized UTF-8-lossy.

### Decisive source
```c
/* Context-bomb guard: a structural node (Module/File) spans its whole file,
 * so an unclipped read returned the ENTIRE source — a field-eval agent that
 * fell back to a Module snippet pulled 400KB in one call. Cap the line span
 * (far above any real function) and flag it; the exact range is still in
 * start_line/end_line for a targeted re-read. */
if (end - start + 1 > MCP_SNIPPET_MAX_LINES) {
    end = start + MCP_SNIPPET_MAX_LINES - 1;
    snippet_clipped = true;
}
```

**Flow:** resolve node → compute span (default small window when end ≤ start) → clamp to 500 lines and flag → read file slice → lossy-UTF-8 sanitize → emit; match_method omitted for exact matches so agents can distinguish fuzzy hits.
**Invariant:** The flag is mandatory whenever clipping happens — silent truncation would corrupt the agent's belief about the file; never clip below what any plausible function needs.
**Probe:** `tests/test_mcp.c:tool_get_code_snippet_clips_whole_file_node` (2000-line Module ⇒ `source_clipped:true`, response < 60000 bytes, first line present, last absent) and `tool_get_code_snippet_not_found`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "build_snippet_response", limit: 5 });
```

## Verdict
Adopt cap+flag+exact-range-preserved for any source-serving tool; adapt the limit to your token budget; omit neighbor inclusion if your UI supplies it separately.
