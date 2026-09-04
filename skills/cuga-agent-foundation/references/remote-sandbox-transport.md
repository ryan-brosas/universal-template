<!-- capsule-v2 -->
# E2B remote transport — source-code tool serialization, sentinel locals split, and knowledge-scope stubs

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When generated code runs in a REMOTE sandbox, your in-process async tools don't exist there. How do you move the tool surface across the boundary — and how do you get computed variables BACK from a one-way stdout stream?

## The remote executor
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/e2b/e2b_executor.py` (`E2BExecutor.execute_for_cuga_lite` :39-116, `_serialize_tools` :163-216, `_serialize_knowledge_tool_stub` :218-269, `_parse_execution_output` :271-296).
**Signature:** `execute_for_cuga_lite(wrapped_code, context_locals, state, thread_id=None, apps_list=None) -> (result, parsed_locals)`; `_serialize_tools(locals_dict, apps_list=None) -> str`.
**Data Shape:** complete_code = call_api helper + serialized tool defs + formatted variables + wrapped code + a `main()` that prints sentinel `"!!!===!!!"` then `__result_locals`; parse splits stdout on that exact sentinel and literal-evals the LAST `{`-starting line.

### Decisive source
```python
# e2b_executor.py:92-95 — the return channel is stdout with an exact sentinel
async def main():
    __result_locals = await asyncio.wait_for(_async_main(), timeout={sandbox_timeout})
    print("!!!===!!!")
    print(__result_locals)

# e2b_executor.py:184-206 — registry wrappers have no own source: emit call_api stubs
if f"def {tool_name}" in dedented_source or f"async def {tool_name}" in dedented_source:
    lines.append(dedented_source)          # real source travels as-is
else:
    ...
    stub = f'async def {tool_name}(**kwargs):\n    return await call_api("{app_name_guess}", "{api_name_guess}", kwargs)'
```

**Flow:** serialize every non-underscore coroutine function: knowledge tools (tagged `_knowledge_allowed_scopes`) get scope-validating stubs; tools whose `inspect.getsource` contains their own def travel verbatim; registry wrappers become `call_api(app, api, kwargs)` stubs with app guessed longest-app-prefix-first then first-segment fallback; unsourceable callables degrade to an `"unknown"`-app stub. Variables arrive via `variables_manager.get_variables_formatted()`. Parse phase: no sentinel → whole output is the result with empty locals; sentinel → last parseable `{...}` line wins (walks backwards, skipping unparseable candidates).
**Invariant:** the sandbox timeout is `int()`-cast BEFORE template substitution — a misconfigured string would inject syntactically broken Python and surface as a confusing sandbox NameError instead of failing early here. Knowledge stubs inject `thread_id` only when blank/None (setdefault would keep explicit `""`, which produced live post-publish 400s) and emit scope/thread blocks ONLY for tools whose declared positional args accept them — silently injecting absent params would TypeError inside the sandbox.

**Probe:** direct tests `executors/tests/test_e2b_lite.py`, `executors/tests/test_e2b_direct.py` (live-sandbox gated); `executors/tests/test_api_calls_with_print.py` pins the call_api + print interaction. Coverage caveat: E2B paths need network/sandbox credentials — CI exercises them behind markers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "E2BExecutor _serialize_tools _parse_execution_output execute_for_cuga_lite", limit: 10 });
```

## Verdict
Adopt source-travel for real functions + call_api-stub synthesis for registry wrappers, and the stdout-sentinel locals-return channel (with last-parseable-line tolerance). Adapt the sentinel string and app-name guessing to your RPC shape. Omit knowledge-tool scope stubs unless you run scoped retrieval tools remotely.
