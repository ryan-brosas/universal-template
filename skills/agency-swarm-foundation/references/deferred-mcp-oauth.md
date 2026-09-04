<!-- capsule-v2 -->
# Deferred MCP activation — how do OAuth-protected servers expose an auth tool instead of failing discovery at startup?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How are OAuth MCP servers split out of eager conversion, activated model-triggered mid-run, and kept per-user isolated?

## Split → authenticate_mcp_server tool → scoped runtime storage
**Path/Symbol:** `src/agency_swarm/agent/core.py:_split_deferred_oauth_mcp_servers` (:466-494), `_prepare_deferred_oauth_mcp_servers` (:496-519), `_install_mcp_authentication_tool` (:521-666); storage `src/agency_swarm/agent/context_types.py:AgentRuntimeState.scoped_oauth_mcp_tools` (:43-54).
**Signature:** `_activate_mcp_server(ctx, server_name) -> str` (inner); activation tool `authenticate_mcp_server(server_name: str)` with enum-restricted param; `convert_mcp_servers_to_tools(agent, *, add_to_agent=True) -> list[FunctionTool]` in `tools/mcp_manager.py` (:181-219).
**Data Shape:** deferred map `_oauth_mcp_servers: dict[name, server]`; converted tools stored per `(runtime_state, owner_user_id)`; tool name `authenticate_mcp_server` is RESERVED — a user tool with that name raises.

### Decisive source
```python
# Startup: stage OAuth servers WITHOUT connecting or listing tools
self._oauth_mcp_servers.update(deferred_servers)
self.mcp_servers = eager_servers                      # only non-OAuth go through conversion now
self._install_mcp_authentication_tool(sorted(self._oauth_mcp_servers))
...
# Activation (mid-run, LLM-invoked): swap in ONE server, convert OFF the loop, restore
self.mcp_servers = [selected]
conversion_task = asyncio.create_task(asyncio.to_thread(convert_mcp_servers_to_tools, self, add_to_agent=False))
while not conversion_task.done():
    try: await asyncio.shield(conversion_task)
    except asyncio.CancelledError as exc: cancellation = exc   # finish conversion, then re-raise
...
_store_mcp_server_tools(runtime_state, _resolve_oauth_owner_id(ctx.context), server_name, conversion_task.result())
...
finally:
    self.mcp_servers = original_servers               # ALWAYS restored, success or fail

def scoped_oauth_mcp_tools(self, user_id):
    if self.oauth_mcp_tools_user_id != user_id:
        self.oauth_mcp_tools = {}                     # user switch DISCARDS prior tools
        self.oauth_mcp_tools_user_id = user_id
    return self.oauth_mcp_tools
```

**Flow:** constructor splits (duplicate names RAISE) → installs activation tool whose schema enum lists deferred names → at run time `get_all_tools` strips stale MCP-tagged static tools and appends runtime send-message + OWNER-scoped OAuth tools → LLM calls `authenticate_mcp_server("name")` → conversion runs on a worker thread (shielded against cancellation mid-write), tools tagged `_agency_swarm_mcp_server_name`, one-call-guarded, stored under the active OAuth owner → re-auth returns "Retry the MCP tool call." so the model re-issues its original call.
**Invariant:** (1) Discovery/auth NEVER blocks startup — the cost is a reserved tool name and enum plumbing; (2) activated tools belong to the authenticated session that made them, so a user switch must DROP the previous user's tools rather than serve them cross-account; (3) cancellation during conversion completes the task before propagating (partial tool lists would corrupt the agent's tool set); (4) `mcp_servers` mutation is always wrapped save/restore because the same list object is shared across concurrent contexts.
**Probe:** `tests/integration/mcp/test_mcp_integration.py::test_mcp_stdio_get_response` (:49), `test_mcp_proxy_enters_async_context_when_session_reset` (:67); duplicate-name contract pinned inside `tests/integration/mcp/test_mcp_server.py::test_mcp_unsupported_tool_type` (:391)/`:402`. Coverage caveat: the OAuth split/activation path itself has no dedicated unit suite at HEAD — verified by whole-file source read + integration MCP suites exercising the surrounding lifecycle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "deferred oauth mcp servers authenticate_mcp_server", limit: 10 });
```

## Verdict
Adopt deferred activation with a reserved auth-tool + enum and owner-scoped tool storage; adapt to your MCP client's connect/list API; omit the thread-offload dance if your conversion is already async-native. Integration suites pin the surrounding lifecycle; activation internals carry a stated coverage caveat.
