<!-- capsule-v2 -->
# Two-layer tool serialization — asyncio.Lock inside, profile lease across processes

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How does an MCP server serialize concurrent tool calls against ONE shared browser, across both sessions and processes?

## SequentialToolExecutionMiddleware
**Path/Symbol:** `linkedin_mcp_server/sequential_tool_middleware.py` (:1-136, whole module); lease handoff via `drivers/browser.release_profile_if_idle_or_requested()`.
**Signature:** `on_call_tool(context, call_next) -> ToolResult`; inner `asyncio.Lock`; outer `get_profile_lease().try_acquire()` then `await lease.acquire(timeout=get_config().browser.browser_wait_seconds)`.
**Data Shape:** Progress messages at each transition ("Queued waiting for scraper lock" → "Scraper lock acquired" → "waiting for it to hand over") via `fastmcp_context.report_progress`.

### Decisive source
```python
# Two layers, because one is not enough:
#
# * an ``asyncio.Lock`` serializes calls inside this process, where several
#   MCP sessions can share one server;
# * the profile lease serializes calls across processes, where each MCP
#   client instance spawns its own server against the same Chromium profile.
#
# Without the second layer two processes open that profile simultaneously
# and the last one to close silently overwrites the other's cookies.
...
if not acquired:
    # Raised as a ToolError here, not via error_handler: an exception
    # thrown in middleware does not pass through raise_tool_error, and
    # mask_error_details would otherwise hide the explanation.
    raise ToolError(str(BrowserBusyError()))
...
try:
    note_call_started()
    return await call_next(context)
finally:
    note_activity()
    lease.release()
    await release_profile_if_idle_or_requested()
```
**Flow:** queue on in-process lock → try nonblocking lease acquire → bounded wait with progress feedback → give up as `BrowserBusyError` ToolError → mark call started (balances in finally even on cancel) → run → release lease → immediate idle-handoff so a waiter gets the browser instead of this process holding it for life.
**Invariant:** In-process and cross-process serialization are DIFFERENT problems needing different primitives; middleware exceptions bypass normal error channels (raise ToolError directly or masking hides your message); finally-block bookkeeping must balance even under cancellation.
**Probe:** `tests/test_profile_lease_integration.py` (1,594L) pins cross-process serialization + handoff.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "SequentialToolExecutionMiddleware BrowserBusyError note_call_started", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer pattern for any shared-resource MCP/tool server. Adapt budget config name. Omit FastMCP-specific plumbing.
