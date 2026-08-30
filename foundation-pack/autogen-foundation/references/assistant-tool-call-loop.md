<!-- capsule-v2 -->
# AssistantAgent tool-call loop — how do you bound a model↔tool loop so concurrent tool results stay coherent?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** Where is the loop bounded, when do tool results enter the model context, and why do tool failures never raise?

## Bounded loop with gather barrier and None-sentinel stream
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py` (`_process_model_result` :1118–1325, inner `_execute_tool_calls` :1196–1217, `_execute_tool_call` :1536–1624).
**Signature:** `async def _process_model_result(cls, model_result: CreateResult, ..., max_tool_iterations: int, output_content_type: type[BaseModel] | None, message_id: str, ...) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]`.
**Data Shape:** `CreateResult.content` is `str` (final answer) or `List[FunctionCall]`; each call executes to `(FunctionCall, FunctionExecutionResult)`; streaming events funnel through an `asyncio.Queue` whose `None` entry means "all tools done".

### Decisive source
```python
for loop_iteration in range(max_tool_iterations):
    # If direct text response (string), we're done
    if isinstance(current_model_result.content, str):
        ...
        yield Response(chat_message=TextMessage(...), inner_messages=inner_messages)
        return
    ...
    results = await asyncio.gather(*[cls._execute_tool_call(tool_call=call, ...) for call in function_calls])
    # Signal the end of streaming by putting None in the queue.
    stream_queue.put_nowait(None)
    ...
    # Wait for all tool calls to complete.
    executed_calls_and_results = await task
    exec_results = [result for _, result in executed_calls_and_results]
    await model_context.add_message(FunctionExecutionResultMessage(content=exec_results))
```
```python
# _execute_tool_call failure arms — errors become RESULTS, never exceptions:
except json.JSONDecodeError as e:
    return (tool_call, FunctionExecutionResult(content=f"Error: {e}", call_id=tool_call.id, is_error=True, name=tool_call.name))
...
return (tool_call, FunctionExecutionResult(
    content=f"Error: tool '{tool_call.name}' not found in any workbench",
    call_id=tool_call.id, is_error=True, name=tool_call.name))
```

**Flow:** string content ⇒ immediate `Response` + return · else spawn one task gathering ALL tool calls concurrently while the consumer drains the stream queue until `None` · `ToolCallExecutionEvent` yielded and the combined `FunctionExecutionResultMessage` added to context only after every call finishes · handoff check (:1245–1254) may yield+return BEFORE reflection · last iteration breaks to the tail · otherwise another `_call_llm` (a `thought` regenerates `message_id` :1289–1290) and the loop repeats · after the loop: `reflect_on_tool_use` ⇒ extra LLM reflection flow, else `_summarize_tool_use` deterministic summary.
**Invariant:** the loop makes EXACTLY `max_tool_iterations` LLM calls when every turn returns function calls; malformed arguments and unknown tool names degrade to `is_error=True` results the model can read and recover from in-conversation; intermediate events are observable while execution is still running (stream queue), but context mutation waits for the gather barrier.
**Probe:** `python/packages/autogen-agentchat/tests/test_assistant_agent.py::TestAssistantAgentToolCallLoop::test_tool_call_loop_max_iterations` (:636–675 — 15 queued responses, `max_tool_iterations=5` ⇒ `len(model_client.create_calls) == 5`); also `::test_tool_call_loop_enabled`, `::test_tool_call_loop_disabled_default`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "max_tool_iterations tool call loop error result", file_pattern: "*tests/test_assistant_agent.py", limit: 14 });
```

## Verdict
Adopt the range-bounded loop, gather-before-context-mutation, None-sentinel event streaming, and error-as-result tool contract for any agent that interleaves LLM turns with tools. Adapt the workbench/tool-lookup abstraction to your host's registry. Omit the structured-output (`output_content_type.model_validate_json`) branch and handoff pre-checks if your port has no structured messages or swarm handoffs.
