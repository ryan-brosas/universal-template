<!-- capsule-v2 -->
# Requires-action tool handoff — extract, bridge, invoke, submit; the streaming asymmetry

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does a paused server run get its tool results back, and why does the streaming path raise where the non-streaming path falls through?

## get_function_call_contents + _invoke_function_calls + _format_tool_outputs
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/assistant_content_generation.py:get_function_call_contents` (372–395); `python/semantic_kernel/agents/open_ai/assistant_thread_actions.py:_handle_streaming_requires_action` (576–614), `_invoke_function_calls` (687–707), `_format_tool_outputs` (709–726); `python/semantic_kernel/agents/open_ai/function_action_result.py:FunctionActionResult` (14–19).
**Signature:** `def get_function_call_contents(run: "Run", function_steps: dict[str, FunctionCallContent]) -> list[FunctionCallContent]`; `async def _invoke_function_calls(cls, kernel, fccs, chat_history, arguments, function_choice_behavior=None) -> list["AutoFunctionInvocationContext | None"]`; `def _format_tool_outputs(cls, fccs, chat_history) -> list[dict[str, str]]`.
**Data Shape:** `function_steps` is an id→FunctionCallContent bridge dict that lives across the whole run loop (registered at extraction, consumed at step replay). `FunctionActionResult` is a 3-tuple dataclass: (function_call_streaming_content, function_result_streaming_content, tool_outputs).

### Decisive source
```python
# extraction (assistant_content_generation.py)
required_action = getattr(run, "required_action", None)
if not required_action or not getattr(required_action, "submit_tool_outputs", False):
    return function_call_contents
for tool in required_action.submit_tool_outputs.tool_calls:
    fcc = FunctionCallContent(id=tool.id, index=getattr(tool, "index", None),
                              name=tool.function.name, arguments=tool.function.arguments)
    function_call_contents.append(fcc)
    function_steps[tool.id] = fcc          # bridge for later step replay

# invocation (assistant_thread_actions.py) — FRESH ChatHistory, one gather
return await asyncio.gather(*[
    kernel.invoke_function_call(function_call=function_call, chat_history=chat_history,
                                arguments=arguments, function_behavior=function_choice_behavior)
    for function_call in fccs])

# submission formatting — id-keyed lookup, str()-ified, silent drop
tool_call_lookup = {tool_call.id: tool_call for message in chat_history.messages
                    for tool_call in message.items
                    if isinstance(tool_call, FunctionResultContent) and tool_call.id is not None}
return [{"tool_call_id": fcc.id, "output": str(tool_call_lookup[fcc.id].result)}
        for fcc in fccs if fcc.id in tool_call_lookup]
```

**Flow:** When a run enters `requires_action`, `get_function_call_contents` extracts the pending
tool calls (getattr-guarded so partial SDK objects degrade to an empty list) and registers each
FCC in the run-scoped `function_steps` bridge. The non-streaming `invoke` path yields the function
call content (invisible), invokes all FCCs in one `asyncio.gather` over `kernel.invoke_function_call`
against a FRESH `ChatHistory`, formats `{tool_call_id, output}` pairs via the id-keyed lookup
(`str()`-ified results; FCCs without a matching result are silently dropped), submits them with
`submit_tool_outputs`, and `continue`s the run loop. The streaming path routes through
`_handle_streaming_requires_action`, which returns a `FunctionActionResult` 3-tuple (call content,
merged streaming result via `merge_streaming_function_results`, tool outputs) for the caller to
submit.
**Invariant:** ASYMMETRY: when extraction yields nothing, the streaming path raises
`AgentInvokeException("Function call required but no function steps found")` while the
non-streaming path silently falls through to step listing (the run may have completed between
poll and extraction). The `function_steps` bridge must survive across loop iterations — step
replay later resolves `tool_call.id → FunctionCallContent` through it to build
`FunctionResultContent` with the original function name/plugin/id.
**Probe:** `python/tests/unit/agents/openai_assistant/test_assistant_thread_actions.py::mock_thread_requires_action_run` (fixture, 236–269), `test_handle_streaming_requires_action_returns_result` (800–840), `test_handle_streaming_requires_action_returns_none` (841–860), `test_assistant_thread_actions_stream_with_instructions` (678–767, event sequence incl. requires_action).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "get_function_call_contents _format_tool_outputs submit_tool_outputs function_steps", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the extract→bridge→gather→format→submit handoff with an id-keyed bridge that outlives the loop iteration, and str()-ified tool outputs keyed by call id. Adapt the silent-drop policy for missing results (SK drops them; you may prefer an explicit error output). Omit the streaming raise if your transport cannot pause mid-stream — but then document that empty extraction falls through instead.
