<!-- capsule-v2 -->
# @tool decorator — how do you register async functions AND class methods as tools from one decorator, with fail-safe timeline summaries?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What is the minimal tool-authoring surface that keeps self-binding working and never lets summary code break the loop?

## FunctionTool vs metadata-only ToolMeta
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/decorators.py` — module docstring (1-39), `_default_terminal_outcome` (67-87), `_safe_summarize_args/_safe_summarize_result` (94-114), `_is_method` (117-124), `FunctionTool` (132-231), `ToolMeta` (239-260), `BoundMethodTool` (later half of file).
**Signature:** `@tool(path="/toolsets/web/search", short_description=..., description=..., parameters=[ToolParameter(...)], tags=[...], args_summary=<fn>, result_summary=<fn>)`.
**Data Shape:** First param named `self`/`cls` ⇒ method mode: annotate with frozen `ToolMeta`, method stays callable with normal binding; a `ToolsetBuilder` later collects metas into `BoundMethodTool`s. Otherwise ⇒ replaced by a `FunctionTool` wrapping the coroutine. Name derives as `{app}__{leaf}` from path segments.

### Decisive source
```python
# decorators.py:94-103 — a contributor's one-line lambda is arbitrary code;
# a typo must degrade to "no summary", not break the tool loop.
def _safe_summarize_args(formatter, args):
    if formatter is None:
        return None
    try:
        return formatter(args)
    except Exception:
        return None
```

**Flow:** declaration → registration (`registry.register_tool(fn_tool)` standalone, or `toolset.register_into(registry)` for class instances) → turn loop resolves the tool and asks `summarize_args`/`summarize_result` (tool-declared formatter first, runtime summarizer second, None last — see tool-loop capsule) for event payloads. Terminal opt-in: a `@tool(tags=[TAG_LIFECYCLE_TERMINAL])` tool gets the shared `_default_terminal_outcome` — stop the run, return this turn's assistant text as final output, NEVER refuse on empty (unlike task_complete's refusal rule).
**Invariant:** Summarizer exceptions are swallowed to None everywhere (emitters treat None as "use raw preview"); only `async def` functions may be wrapped (TypeError otherwise); original function preserved on `.func` for direct test invocation bypassing validation.
**Probe:** `tests/unit/agent_loop_lib/tools/test_decorator_summarizers.py::test_delegates_to_declared_args_summary` (:75), `::test_args_summary_exception_degrades_to_none` (:90), `::test_result_summary_exception_degrades_to_none` (:97), `::test_summarize_args_defaults_to_none` (:26).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "FunctionTool BoundMethodTool ToolMeta args_summary terminal outcome", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-mode decorator with inspect-based self detection, exception-proof colocated summaries, and the permissive default terminal outcome; adapt path/name conventions and the parameter type enum to host; omit result_schema passthrough unless your frontend renders typed results. Direct tests cover delegation and both degrade-to-None branches.
