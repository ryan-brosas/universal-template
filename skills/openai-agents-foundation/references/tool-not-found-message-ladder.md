<!-- capsule-v2 -->
# Tool-not-found message ladder — how does a call to a missing tool become model feedback instead of a crash?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When the model calls a function that no agent exposes, how do you decide between raising and returning an error to the model, let a user formatter customize the error text without being able to break the turn, and guarantee exactly one `function_call_output` for the missing call on both live and resume paths?

## Detection branch + fail-soft formatter resolution + shared item builder
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py:` detection in `process_model_response` (:3382–3400), `_default_tool_not_found_message` (:258–259), `_resolve_tool_not_found_message` (:262–307), `_build_tool_not_found_output_items` (:309–333); call sites `execute_tools_and_side_effects` (:877–883) and `resolve_interrupted_turn` (:2416–2422); `src/agents/run_context.py:` `_mark_tool_invocation_executed` (:489–501); `src/agents/run_internal/run_steps.py:` `ToolRunFunctionNotFound` (:75).
**Signature:** `_resolve_tool_not_found_message(*, context_wrapper, run_config, tool_call, tool_name, call_id) -> str`; `_build_tool_not_found_output_items(*, agent, calls: Sequence[ToolRunFunctionNotFound], context_wrapper, run_config) -> list[RunItem]`.
**Data Shape:** input = unmatched `ResponseFunctionToolCall` + `RunConfig(tool_not_found_behavior: "raise_error" | "return_error_to_model", tool_error_formatter: Callable[[ToolErrorFormatterArgs], MaybeAwaitable[str | None]] | None)`; output = one `ToolCallOutputItem(output=message, raw_item=ItemHelpers.tool_call_output_item(call, message))` per missing call; formatter args carry `kind="tool_not_found"`, `tool_type="function"`, `tool_name`, `call_id`, `default_message`, `run_context`.

### Decisive source
```python
# process_model_response: span error first, then the behavior branch
_error_tracing.attach_error_to_current_span(
    SpanError(message="Tool not found", data={"tool_name": qualified_output_name or output.name})
)
if run_config is not None and (run_config.tool_not_found_behavior == "return_error_to_model"):
    items.append(ToolCallItem(raw_item=output, agent=agent))
    function_tools_not_found.append(ToolRunFunctionNotFound(tool_call=output, tool_name=tool_name))
    continue
error = f"Tool {qualified_output_name or output.name} not found in agent {agent.name}"
raise ModelBehaviorError(error)

# _resolve_tool_not_found_message: fail-soft around user code
context_wrapper._mark_tool_invocation_executed(tool_call)   # BEFORE any user-code side effect
try:
    maybe_message = formatter(ToolErrorFormatterArgs(kind="tool_not_found", ..., default_message=default_message, ...))
    message = await maybe_message if inspect.isawaitable(maybe_message) else maybe_message
except Exception as exc:
    log_tool_action_error(logger, "Tool error formatter failed for missing tool", exc)
    return default_message
if message is None:
    return default_message
if not isinstance(message, str):
    logger.error("Tool error formatter returned non-string for missing tool %s: %s", ...)
    return default_message
```

**Flow:** process_model_response matches each function call against the agent's tools; on a miss it attaches a `SpanError("Tool not found")` to the current tracing span FIRST (tracing always sees the miss), then branches: `tool_not_found_behavior == "return_error_to_model"` records a `ToolCallItem` plus a `ToolRunFunctionNotFound` and continues dispatching the rest of the turn; any other value raises `ModelBehaviorError`. Later, both `execute_tools_and_side_effects` (live) and `resolve_interrupted_turn` (resume, where `missing_function_tools` is collected during approval reconciliation) feed their not-found lists through `_build_tool_not_found_output_items`, which resolves each message via `_resolve_tool_not_found_message`: no formatter → default `Tool '{name}' not found.`; with a formatter → mark the invocation executed on the context wrapper before calling it (so invocation-status/dedupe tracking treats the missing call as processed), await if awaitable, and fall back to the default on exception, `None`, or non-string results. The resolved string becomes a `ToolCallOutputItem` whose raw item is built by `ItemHelpers.tool_call_output_item`, so the model receives a normal `function_call_output` it can react to on the next turn.
**Invariant:** the ladder is total — every formatter failure mode degrades to the default message (the formatter can customize but never break the turn), the original `ModelSettings` escape hatches are never mutated, and a missing call yields exactly ONE output item whether discovered live or during resume reconciliation.
**Probe:** `tests/test_agent_runner.py::test_tool_not_found_behavior_returns_error_to_model` (:6695 — second-turn input contains `{"call_id": "call_missing", "output": "Tool 'missing_tool' not found."}`), `::test_tool_not_found_behavior_uses_tool_error_formatter` (:6729 — async formatter with `kind == "tool_not_found"` produces `"missing_tool unavailable for call_missing"`), `tests/test_process_model_response.py::test_process_model_response_collects_missing_function_tool_when_opted_in` (:913 — `function_tools_not_found[0].tool_name == "missing_tool"`), `tests/test_run_config.py::test_tool_not_found_behavior_defaults_to_raise_error` (:382).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "turn_resolution.py", query: "tool not found behavior return error to model", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.turn_resolution._resolve_tool_not_found_message" });
```

## Verdict
Adopt the two-mode miss contract (raise vs return-to-model) with the span error attached before the branch, the fail-soft formatter (exception/None/non-string all fall back to the default), and the mark-executed-before-user-code ordering for any framework that turns unknown-tool calls into model feedback. Adapt the behavior enum names and the formatter argument shape. Omit the resume-path item builder if your runner has no interrupted-state reconciliation. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); decisive ranges read from checkout at fe45b415.
