<!-- capsule-v2 -->
# StepExecutor — how does one plan step run in isolation with its own multi-turn tool loop and no shared state?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What is the exact contract of the per-step worker (inputs, loop bounds, fallback, result), and what must NOT leak between it and the orchestrator?

## StepExecutor.execute
**Path/Symbol:** `lib/crewai/src/crewai/src/../agents/step_executor.py:64-242` (`class StepExecutor`, `execute`), loops at `:328-378` (`_execute_text_parsed`) and `:539-589` (`_execute_native`).
**Signature:** `def execute(self, todo: TodoItem, context: StepExecutionContext, max_step_iterations: int = 15, step_timeout: int | None = None) -> StepResult`.
**Data Shape:** In: frozen `StepExecutionContext(task_description, task_goal, dependency_results: dict[int, str])`. Out: frozen `StepResult(success, result, error=None, tool_calls_made=[], execution_time=0.0)` — "Tool call details are for audit logging only — they are NOT passed to subsequent steps or the Planner."

### Decisive source
```python
# module docstring: "There is no inner loop. Recovery from failure (retry,
# replan) is the responsibility of PlannerObserver and AgentExecutor."
for _ in range(max_step_iterations):                      # native variant
    if step_timeout and start_time:
        elapsed = time.monotonic() - start_time
        if elapsed >= step_timeout:
            return ("\n\n".join(accumulated_results)
                    if accumulated_results
                    else f"Step timed out after {elapsed:.0f}s")
    answer = self.llm.call(messages, tools=self._openai_tools, ...)
    if isinstance(answer, BaseModel): return answer.model_dump_json()
    if isinstance(answer, list) and answer and is_tool_call_list(answer):
        accumulated_results.append(self._execute_native_tool_calls(...)); continue
    return str(answer)                                    # text == done

# native→text downgrade KEEPS the conversation built so far:
except Exception as e:
    if self._use_native_tools and is_native_tool_calling_unsupported_error(e):
        self._use_native_tools = False; ...
        # "append the text-tooling instructions instead of restarting the
        #  step, so completed tool calls are not re-executed"
        messages.append(format_message_for_llm(
            build_text_tool_calling_fallback_message(...), role="user"))
```

**Flow:** Build isolated messages (system = Executor persona from agent role/goal/backstory; user = extracted task section + step description + suggested tool + sorted dependency results) → loop LLM call → execute tool batch → append observation → until text answer / iterations exhausted. Timeout returns partial results rather than failing. After the loop `_validate_expected_tool_usage` raises ValueError when `todo.tool_to_use` names an available tool that was never called — a plan-level contract violation. Exceptions become `StepResult(success=False, error=str(e))` EXCEPT deliberate stops: `ToolExecutionFailedError` is re-raised ("StepResult(success=False) would let the plan carry on"). Vision sentinel: a tool result starting `VISION_IMAGE:<media_type>:<base64>` is converted into an `image_url` content block so the model sees pixels, not base64 text.
**Invariant:** The worker NEVER reads or writes AgentExecutor state; results cross only via the two frozen dataclasses. A porter who lets StepExecutor touch shared messages reintroduces exactly the coupling Plan-and-Act removes — parallel steps would interleave each other's histories.
**Probe:** `tests/agents/test_agent_executor.py::test_step_executor_fails_when_expected_tool_is_not_called`, `test_step_executor_text_tool_emits_usage_events`, `test_step_executor_falls_back_when_native_tools_are_rejected`, `test_step_executor_uses_standard_image_url_format` (all under `TestStepExecutor*`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "StepExecutor execute todo", limit: 6, detail: "ids" });
// → StepExecutor.execute 127-242; _execute_native 539-589; _execute_text_parsed 328-378
```

## Verdict
Adopt the stateless single-step worker with conversation-preserving provider downgrade and expected-tool validation; adapt prompt templates/i18n keys to your host; omit the vision-sentinel converter if your tools return structured image blocks natively.
