<!-- capsule-v2 -->
# MCP cancellation scoping — how do you honor notifications/cancelled without killing the wrong request?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What bookkeeping matches a cancel notification to the in-flight tool call, and why a request-scope depth counter?

## Active-id match + scoped depth + reset-on-begin
**Path/Symbol:** `src/mcp/mcp.c:cbm_mcp_cancel_request_matches` (340–365), `cbm_mcp_server_cancel_active` (1837–1848), `cbm_mcp_server_request_scope_begin` (1850–1864); dispatch wiring 11726–11745.
**Signature:** `bool cbm_mcp_cancel_request_matches(const char *params_json, int64_t active_id, const char *active_id_str);`
**Data Shape:** Cancel params carry `requestId` as int OR string — matching must use whichever form the ACTIVE request used (`active_id_str ? string-compare : int-compare`). Server keeps `request_scope_depth`, `active_request_id(+_str)`, atomic `pipeline_cancel_requested`.

### Decisive source
```c
if (!req.has_id) {  /* notifications → handle cancellation, then NO response */
    if (req.method && strcmp(req.method, "notifications/cancelled") == 0) {
        if (cbm_mcp_cancel_request_matches(req.params_raw, srv->active_request_id,
                                           srv->active_request_id_str) &&
            cbm_mcp_server_cancel_active(srv)) { ... } }
    cbm_jsonrpc_request_free(&req); return NULL; }
```
```c
if (srv->request_scope_depth == 0)
    atomic_store_explicit(&srv->pipeline_cancel_requested, 0, memory_order_release);
srv->request_scope_depth++;
```

**Flow:** tools/call stores its id (+string form) and begins scope → long-running pipeline polls the atomic flag → notification arrives with no id field, is matched against BOTH id representations, and only then flips the flag → scope_end decrements; reaching zero CLEARS the flag so the NEXT request starts clean.
**Invariant:** A text mention of "cancelled" inside string content must NOT trigger (frontend tests pin this); clearing happens at depth-0, never per nested call.
**Probe:** `tests/test_mcp.c:mcp_cancel_matches_request_id`, `tool_raw_dispatch_cancel_is_scoped_non_mutating_and_next_request_clean`, `tool_outer_request_scope_preserves_predispatch_cancel`; frontend twins in tests/test_daemon_frontend.c:1076–1129.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_mcp_cancel_request_matches", limit: 5 });
```

## Verdict
Adopt dual-representation id matching + depth-scoped flag reset for JSON-RPC cancellation; adapt to your transport framing; omit the diagnostics logging if you lack an event sink.
