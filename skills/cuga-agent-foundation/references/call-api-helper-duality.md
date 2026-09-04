<!-- capsule-v2 -->
# call_api helper duality — local tracker-first vs remote injected-source tool calls

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does generated agent code reach registered tools identically whether it executes in-process (local executor) or inside a remote sandbox (E2B/Docker), and which side-channel plumbing must survive?

## CallApiHelper: same contract, two carriers
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/common/call_api_helper.py` (`get_function_call_url` :12-24, `get_trajectory_path` :27-33, `create_local_call_api_function` :36-150, `create_remote_call_api_code` :153-231, deprecated alias `create_call_api_code` :235-237).
**Signature:** local → returns an async `call_api(app_name, api_name, args=None, operation_id=None)` closure; remote → returns a SOURCE STRING defining `async def call_api(app_name, api_name, args=None)` to inject into the sandbox preamble.
**Data Shape:** both funnel through the registry server's `POST {registry_base}/functions/call` with payload `{app_name|function_name|args}`; local additionally consults `ActivityTracker.tools` FIRST (runtime-registered tools never hit HTTP).

### Decisive source
```python
# call_api_helper.py:79-95 — tracker-first with uniform dict coercion
if tracker.tools and app_name in tracker.tools:
    result = await asyncio.wait_for(
        tracker.invoke_tool(app_name, api_name, args), timeout=timeout_seconds)
    ...
    if not isinstance(result, dict):
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, '__dict__'):
            result = result.__dict__
        else:
            result = str(result)
    return result
```
Remote side pins the stdlib-only transport: `urllib.request` executed via `loop.run_in_executor(None, _do_request)` (no aiohttp in the sandbox), `socket.timeout` and URLError-with-timeout-reason BOTH mapped to an explicit timeout message, HTTPError body lifted into the message — mirroring the error-envelope ladder of `tool-call-error-envelope`.

**Flow:** budget enforcement rides the LOCAL path only (`BlockToolCallCounter.increment()` + `ToolCallTracker.enforce_call_budget()` before dispatch; `ToolCallTracker.record_call(... duration_ms, error)` in `finally` — recording happens even when the call raised). Remote calls carry observability as URL plumbing instead: `get_function_call_url()` resolves `settings.server_ports.function_call_host` else `registry_host` else loud-warning fallback `http://localhost:8001`, then appends `?trajectory_path={quote(ActivityTracker().get_current_trajectory_path())}` so benchmark trajectory tracking survives across the sandbox boundary.
**Invariant:** identical `(app_name, api_name, args) → JSON-or-string` semantics on both sides; timeouts surface as explicit "timed out after N seconds" errors, never silent hangs; every local call is recorded exactly once even on failure.
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/tests/test_run_tool_call_cap.py` (:1-45 imports `CallApiHelper`, monkeypatches `cuga.config.settings`, asserts cap enforcement raises recoverable guidance "final answer from the data already retrieved" and per-run carry-over seeding); also `test_tool_call_budget_levels.py`.
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CallApiHelper create_remote_call_api_code", limit: 5 });
```

## Verdict
Adopt the two-carrier pattern (closure for in-process, source-string for sandboxed) plus tracker-first dedup and finally-clause recording. Adapt the registry endpoint and settings keys. Omit the localhost:8000x port guessing only if your host guarantees configuration. Cross-reference: `remote-sandbox-transport.md` (how tools themselves cross), `registry-url-ladder` inside the sandbox-trio map entry.
