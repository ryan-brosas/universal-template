<!-- capsule-v2 -->
# execute_code RPC bridge — how does code running in a sandbox call host tools without bypassing governance?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When the model's script calls `tool(name, **kwargs)` from inside a subprocess, how do you keep permission/approval/mode enforcement identical to model-initiated calls — and which tools must stay unreachable?

## JSON-lines protocol + dispatch through the SAME ToolExecutor funnel
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/rpc.py:ToolBridge/_HARNESS` (L40–210); `backend/python/app/agent_loop_lib/control_plane/control_plane.py:_EXECUTE_CODE_BLOCKED_TOOLS` (L19–25) + `_execute_code_dispatch` (L893–914).
**Signature:** `ToolDispatch = Callable[[str, dict], Awaitable[Any]]`; `ToolBridge(dispatch, working_dir=None, max_tool_calls=50).run(code, timeout=30.0) -> CodeExecResult`.

```python
# Protocol (rpc.py docstring) — JSON Lines over the child's stdout/stdin:
#   child -> host:  {"type": "call", "id": <int>, "tool": <str>, "args": {...}}
#   host  -> child: {"ok": true, "value": <json>} | {"ok": false, "error": <str>}
#   child -> host:  {"type": "done", "stdout": ..., "stderr": ...,
#                     "result": <json|null>, "error": <traceback|null>}
#
# The harness redirects sys.stdout/sys.stderr to in-memory buffers for the
# DURATION of the user's code; the REAL pipes carry only this protocol.

# control_plane.py — the refusal list:
_EXECUTE_CODE_BLOCKED_TOOLS = frozenset({
    "execute_code", "spawn_agent", "best_of_n", "clarify", "write_todos",
    "fetch_tools", "list_toolsets", "search_tools", "replan", "handoff",
    # coding sandbox blocked so a script inside execute_code's own
    # sandboxed subprocess can't recursively spawn a second sandbox.
    "run_code", "install_packages",
})

async def _execute_code_dispatch(self, name, args):
    if name in _EXECUTE_CODE_BLOCKED_TOOLS:
        raise ValueError(f"Tool '{name}' cannot be called from execute_code — call it directly instead.")
    if self._tool_registry is None or not self._tool_registry.has(name):
        raise ValueError(f"Unknown tool: {name!r}")
    call = ToolCall(id=str(_uuid.uuid4()), name=name, arguments=args)
    result = await ToolExecutor(self._tool_registry, self._kernel).call_tool(call)
    if result.is_error:
        raise RuntimeError(str(result.content))
    return result.content
```

**Data Shape:** child ids are a local `itertools.count()`; the host loop enforces `max_tool_calls` (over-limit ⇒ error response, not kill). Non-protocol lines on the shared pipe are ignored (`json.JSONDecodeError: continue`). Timeout kills the child and returns `CodeExecResult(error="Timed out after Ns")`. A global named `result` in the user's script becomes the returned value (repr-fallback if not JSON-serializable).

### Decisive source
```python
# control_plane.py L893-899: "RPC bridge dispatch for `execute_code`
# (sandbox/rpc.py): routes a `tool(name, **kwargs)` call made from INSIDE
# sandboxed code through the exact same `ToolExecutor.call_tool()` —
# PreToolUse -> execute -> PostToolUse — as a normal top-level tool call,
# so permission/approval/mode enforcement is never bypassed just because
# the call originated from code instead of the model directly."
```

**Flow:** host writes harness+user code to temp files → spawns `sys.executable harness.py code.py` with piped stdio → child execs user source with only `tool()` in scope → each `tool()` emits a `call` line and blocks on one response line → host awaits `dispatch` (the full executor funnel incl. hooks) and writes `{ok,value|error}` → child finishes ⇒ single `done` line carries captured stdout/stderr/result/traceback → host re-raises tool errors as RuntimeError so the script sees them.

**Invariant:** the bridge must route through the SAME executor path as model calls — a fast-path that calls `tool.execute()` directly silently bypasses every gate. The blocked set exists because those tools need turn-loop context a bare executor call cannot provide (spawn lifecycle, HIL block/resume, agent-level state mutation) AND to stop recursive sandbox spawning; extending the tool surface means re-auditing this list. Child stdout is protocol-only — user prints are captured and shipped in `done`, never interleaved.
**Probe:** `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py:422-456` (`TestExecuteCodeDispatch`: blocked⇒ValueError "cannot be called from execute_code", unknown⇒ValueError, pre-start⇒ValueError, success returns content, tool error⇒RuntimeError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_execute_code_dispatch ToolBridge max_tool_calls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the same-funnel routing rule, the blocked-tool taxonomy, and the buffer-captured stdio JSON-lines protocol (no extra fds ⇒ portable). Adapt the blocked list to your own context-dependent tools. Omit nothing structural. Coverage caveat: rpc.py itself has no dedicated unit test file in tests/unit/agent_loop_lib/sandbox (only test_docker/local/executor/reflection/validation); its contract is pinned via TestExecuteCodeDispatch against the dispatch closure.
