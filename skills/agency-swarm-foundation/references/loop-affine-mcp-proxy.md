<!-- capsule-v2 -->
# Loop-affine MCP proxy — how do you share one persistent server across event loops without cross-loop await crashes?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How does a server object created on a background loop serve callers running on OTHER loops (or none), and which failures must be re-labeled?

## LoopAffineAsyncProxy over PersistentMCPServerManager
**Path/Symbol:** `src/agency_swarm/tools/mcp_loop_proxy.py:LoopAffineAsyncProxy` (whole file, 75L) + `attach_persistent_mcp_servers` / `register_and_connect_agent_servers` in `src/agency_swarm/tools/mcp_manager.py` (:69-119, :131-178).
**Signature:** `__getattr__(name)` returns an async `_proxy(*args, **kwargs)` for any coroutine attribute; plus `__aenter__`/`__aexit__` routed through the manager; `default_mcp_manager: PersistentMCPServerManager` singleton with `get/register/ensure_connected/_submit_driver_call/_await_future`.
**Data Shape:** every agent's `mcp_servers[i]` entry is REPLACED in place with the proxy (`servers[i] = replacement`); persistence key built from server identity + oauth user segment; per-method timeouts resolved by the manager (`_resolve_method_timeout`, defaults like `__aenter__` 30.0s).

### Decisive source
```python
def __getattr__(self, name):
    target = getattr(self._server, name)
    if inspect.iscoroutinefunction(target):
        async def _proxy(*args, **kwargs):
            timeout = self._manager._resolve_method_timeout(self._server, name)
            fut = self._manager._submit_driver_call(self._server, name, args, kwargs)  # → background loop
            try:
                return await self._manager._await_future(fut, timeout=timeout)          # caller's loop awaits a future
            except TimeoutError as exc:
                raise TimeoutError(f"MCP call '{name}' timed out after {timeout:.1f}s on server '{server_name}'") from exc
            except asyncio.CancelledError as exc:
                if asyncio.current_task() is not None and asyncio.current_task().cancelling():
                    raise                     # caller genuinely cancelled → propagate
                raise RuntimeError(f"MCP call '{name}' was cancelled on server '{server_name}'. ...") from exc
        return _proxy
    return target                             # non-coroutines pass straight through
```

**Flow:** attach time — clone candidate → build persistence key → register-or-fetch shared persistent instance → wrap in LoopAffineAsyncProxy → `ensure_connected` once on the driver loop → call time — any coroutine method is submitted to the owning loop and awaited as a plain future from the caller's loop.
**Invariant:** (1) The proxy replaces (not wraps at call sites) the server reference so ALL later code paths — SDK tool conversion, guardrail stack, FastAPI handlers — inherit loop affinity transparently; (2) a CancelledError raised INSIDE the background call must be re-raised only when the CALLER's task is actually cancelling — otherwise it means the server-side call died and masking it as cancellation would silently drop real errors; (3) timeouts surface as TimeoutError naming method+server+duration so operators can tune per-method budgets; (4) unnamed servers are rejected loudly (`Server ... has no name provided`) because the persistence key requires a name.
**Probe:** `tests/integration/mcp/test_mcp_integration.py::test_mcp_proxy_enters_async_context_when_session_reset` (:67) pins the async-context re-entry path; `tests/integration/mcp/test_mcp_server.py::test_mcp_http_invoke_sample_tool` (:125) pins invocation through the managed instance.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "LoopAffineAsyncProxy submit driver call", limit: 10 });
```

## Verdict
Adopt the replace-with-proxy pattern + future bridging + cancel-disambiguation rule; adapt the manager's keying to your multi-tenancy needs; omit per-method timeout tables if you have global budgets. Integration tests pin both the proxy context path and live invocation at HEAD.
