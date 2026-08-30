<!-- capsule-v2 -->
# Final output from tools — how does a tool result become the run's final answer?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** After a turn's tools execute, how do you decide whether a tool result IS the final output (stopping the loop) versus feeding it back to the model, support name-based and custom stop policies, and keep the same policy authoritative on resume turns?

## tool_use_behavior dispatch ladder + finalization coercion
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py:` `check_for_final_output_from_tools` (:753–781), `_maybe_finalize_from_tool_results` (:216–256); call sites `execute_tools_and_side_effects` (:937) and `resolve_interrupted_turn` (:2656); `src/agents/agent.py:` `ToolsToFinalOutputResult` (:78–88), `ToolsToFinalOutputFunction` (:90–94); `src/agents/run_internal/run_steps.py:` `NOT_FINAL_OUTPUT` (:59).
**Signature:** `check_for_final_output_from_tools(agent, tool_results: list[FunctionToolResult], context_wrapper) -> ToolsToFinalOutputResult`; `agent.tool_use_behavior: "run_llm_again" | "stop_on_first_tool" | {"stop_at_tool_names": list[str]} | Callable[[RunContextWrapper, list[FunctionToolResult]], MaybeAwaitable[ToolsToFinalOutputResult]]`.
**Data Shape:** input = the turn's `FunctionToolResult`s (each with `.tool.name`, `.tool.qualified_name`, `.output`); output = `ToolsToFinalOutputResult(is_final_output: bool, final_output: Any | None)`; when final, the caller runs the normal final-output pipeline (hooks, guardrails, persistence) via `execute_final_output`.

### Decisive source
```python
if not tool_results:
    return NOT_FINAL_OUTPUT
if agent.tool_use_behavior == "run_llm_again":
    return NOT_FINAL_OUTPUT
elif agent.tool_use_behavior == "stop_on_first_tool":
    return ToolsToFinalOutputResult(is_final_output=True, final_output=tool_results[0].output)
elif isinstance(agent.tool_use_behavior, dict):
    names = agent.tool_use_behavior.get("stop_at_tool_names", [])
    for tool_result in tool_results:
        if tool_result.tool.name in names or tool_result.tool.qualified_name in names:
            return ToolsToFinalOutputResult(is_final_output=True, final_output=tool_result.output)
    return ToolsToFinalOutputResult(is_final_output=False, final_output=None)
elif callable(agent.tool_use_behavior):
    result = agent.tool_use_behavior(context_wrapper, tool_results)
    if inspect.isawaitable(result):
        return await result
    return result
logger.error("Invalid tool_use_behavior: %s", agent.tool_use_behavior)
raise UserError(f"Invalid tool_use_behavior: {agent.tool_use_behavior}")
```

**Flow:** after a turn's tools run, `_maybe_finalize_from_tool_results` asks `check_for_final_output_from_tools` for a decision. The ladder is closed and ordered: no results → never final; `"run_llm_again"` → never final (results always feed back to the model); `"stop_on_first_tool"` → the FIRST result's output is the final output regardless of which tool produced it; dict form → scan results in order and stop at the first whose bare `name` OR `qualified_name` is in `stop_at_tool_names` (so namespaced tools match either spelling); callable form → user code decides, sync or async, returning its own result object; any other shape → loud `UserError`. When final, finalization coerces `final_output` to `str` only when the agent's `output_type` is `None` or `str`, logs (but does not raise) when a stop decision produced `None` ("assume you know what you're doing"), and hands off to `execute_final_output` so the output still passes hooks, guardrails, and persistence. The same check runs from both the live path and `resolve_interrupted_turn`, so a resumed turn honors the identical stop policy.
**Invariant:** stop decisions are policy-shaped, not heuristic — the behavior space is a closed ladder with a loud error on unknown shapes, the first matching result wins (order-faithful), and a tool-decided final output goes through exactly the same validation/guardrail/persistence pipeline as a model-decided one.
**Probe:** `tests/test_tool_use_behavior.py::test_no_tool_results_returns_not_final_output` (:48), `::test_run_llm_again_behavior` (:61), `::test_stop_on_first_tool_behavior` (:75), `::test_custom_tool_use_behavior_sync` (:92), `::test_custom_tool_use_behavior_async` (:117), `::test_invalid_tool_use_behavior_raises` (:179), `::test_tool_names_to_stop_at_behavior` (:194 — non-matching tools don't stop; matching one returns its output), `::test_stop_at_tool_names_supports_public_and_qualified_names_for_namespaced_tools` (:232 — both `lookup_account` and `billing.lookup_account` match).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "turn_resolution.py", query: "check for final output from tools stop at tool names", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.turn_resolution.check_for_final_output_from_tools" });
```

## Verdict
Adopt the closed tool_use_behavior ladder (never / first / named / custom-callable) with first-match-wins scanning, dual bare+qualified name matching for namespaced tools, and routing tool-decided finals through the same final-output pipeline as model-decided ones. Adapt the behavior vocabulary and the result type. Omit the resume-path call site if your runner re-executes turns instead of reconciling them. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); decisive ranges read from checkout at fe45b415.
