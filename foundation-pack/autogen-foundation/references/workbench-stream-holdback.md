<!-- capsule-v2 -->
# Workbench stream hold-back — how do you stream tool output while guaranteeing the terminal ToolResult is always last?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** What yield discipline lets a tool emit arbitrary intermediate chunks and still end every consumer's stream with exactly one typed result?

## Hold-back-one: the next item proves the previous one wasn't final
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/tools/_static_workbench.py` `StaticStreamWorkbench.call_tool_stream` :178–225, `_format_errors` :156–167; ABC `python/packages/autogen-core/src/autogen_core/tools/_workbench.py` `ToolResult.to_text` :55–75.
**Signature:** `async def call_tool_stream(self, name: str, arguments: Mapping[str, Any] | None = None, cancellation_token: CancellationToken | None = None, call_id: str | None = None) -> AsyncGenerator[Any | ToolResult, None]`.
**Data Shape:** stream items are `Any` (tool-defined pydantic chunks) with the FINAL item a `ToolResult{name, result: List[TextResultContent|ImageResultContent], is_error: bool}`; discriminated by Python type, not a field.

### Decisive source
```python
if isinstance(tool, StreamTool):
    previous_result: Any | None = None
    try:
        async for result in tool.run_json_stream(arguments, cancellation_token, call_id=call_id):
            if previous_result is not None:
                yield previous_result          # only yielded once something newer arrived
            previous_result = result
        actual_tool_output = previous_result   # the LAST chunk is the run() value
    except Exception as e:
        if previous_result is not None:
            yield previous_result              # flush what already streamed before failing
        result_str = self._format_errors(e)
        yield ToolResult(name=tool.name, result=[TextResultContent(content=result_str)], is_error=True)
        return
```
```python
def _format_errors(self, error: Exception) -> str:
    if hasattr(builtins, "ExceptionGroup") and isinstance(error, builtins.ExceptionGroup):
        for sub_exception in error.exceptions:      # recursive flattening (3.11+)
            error_message += self._format_errors(sub_exception)
    else:
        error_message += f"{str(error)}\n"
    return error_message.strip()
```

**Flow:** unknown name ⇒ single is_error ToolResult (never raises) · StreamTool ⇒ hold-back-one loop, last chunk becomes the return value rendered via `return_value_as_string` · non-stream tool ⇒ fallback to `run_json` + `cancellation_token.link_future` · any exception ⇒ is_error ToolResult carrying flattened message.
**Invariant:** every call_tool_stream consumption ends with exactly ONE ToolResult as the final item, success or failure; intermediate chunks are plain values and consumers must type-check for the terminal. Errors are results (`is_error=True`), mirroring the agent-level error-as-result contract. Known upstream gap: unlike `call_tool` (:102), the stream path does NOT translate override names back to originals — overridden names fail lookup here.
**Probe:** `python/packages/autogen-core/tests/test_workbench.py::test_static_stream_workbench_call_tool_stream` (:192–294 — count-3 stream yields 3 items + 1 ToolResult; mid-stream raise yields held item then error ToolResult; unknown tool yields one not-found ToolResult) and `..._call_tool_stream_cancellation` (:298–313 — token cancelled after 2 items still terminates cleanly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "autogen", qualified_name: "autogen.python.packages.autogen-core.src.autogen_core.tools._static_workbench.StaticStreamWorkbench.call_tool_stream" });
```

## Verdict
Adopt hold-back-one whenever a generator mixes progress chunks with a terminal verdict — it removes the "was that the last item?" ambiguity without a sentinel. Adapt the ToolResult content union to your media types. Omit the override-name translation on the streaming path unless you fix it first; also note `StateicWorkbenchState` (typo included at :19) is the persisted-state schema name you must keep compatible with.
