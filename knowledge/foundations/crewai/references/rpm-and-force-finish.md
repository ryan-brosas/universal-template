<!-- capsule-v2 -->
# RPM throttle + max-iteration force-finish — how are provider rate limits and runaway loops bounded?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How is the requests-per-minute gate enforced before EVERY LLM call, and what happens when max_iter is hit?

## enforce_rpm_limit / RPMController / handle_max_iterations_exceeded
**Path/Symbol:** `lib/crewai/src/crewai/utilities/agent_utils.py:472-481` (`enforce_rpm_limit`), `:363-373` (`has_reached_max_iterations`), `:376-433` (`handle_max_iterations_exceeded`); `utilities/rpm_controller.py:12-89` (`RPMController`).
**Signature:** `def enforce_rpm_limit(request_within_rpm_limit: Callable[[], bool] | None) -> None  # no-op when None`.
**Data Shape:** Executor holds `request_within_rpm_limit` (crew-injected closure over a shared RPMController); `max_iter` default 25 on AgentExecutor (`Field(default=25, exclude=True)`).

### Decisive source
```python
# RPMController.check_or_wait — lock-guarded counter with minute-window reset:
def _check_and_increment() -> bool:
    if self.max_rpm is not None and self._current_rpm < self.max_rpm:
        self._current_rpm += 1
        return True
    self.logger.log("info", "Max RPM reached, waiting for next minute to start.")
    self._wait_for_next_minute()      # time.sleep(60); _current_rpm = 0
    self._current_rpm = 1
    return True

# max iterations → NOT an abort; ONE more call demanding a final answer:
if formatted_answer and hasattr(formatted_answer, "text"):
    assistant_message = (formatted_answer.text
                         + f"\n{I18N_DEFAULT.errors('force_final_answer')}")
else:
    assistant_message = I18N_DEFAULT.errors("force_final_answer")
messages.append(format_message_for_llm(assistant_message, role="assistant"))
answer = llm.call(messages, callbacks=callbacks)
if answer is None or answer == "":
    raise ValueError("Invalid response from LLM call - None or empty.")
formatted = format_answer(answer=answer)
if isinstance(formatted, AgentFinish):
    return formatted
return AgentFinish(thought=formatted.thought, output=formatted.text,
                   text=formatted.text)     # coerce ANY parse into a finish
```

**Flow:** Every LLM entry point (`call_llm_and_parse`, `call_llm_native_tools`, StepExecutor loops) calls `enforce_rpm_limit(self.request_within_rpm_limit)` BEFORE issuing the request — the shared controller blocks (sleeps) once per window when saturated, so parallel crew agents share one budget. The flow router checks `has_reached_max_iterations(iterations, max_iter)` and routes to `ensure_force_final_answer`, which is IDEMPOTENT (`if self.state.is_finished: return "agent_finished"` — the framework may deliver the label twice because two methods can emit `initialized` in one pass) and calls `handle_max_iterations_exceeded`.
**Invariant:** The force-finish path must CONVERT non-finish parses into AgentFinish rather than raising — hitting the iteration cap degrades to "best effort answer now", never kills the run. The RPM gate belongs before the LLM call, not around it, so retries triggered by parser/context errors also consume budget correctly.
**Probe:** `tests/agents/test_agent_executor.py::TestCheckMaxIterations.test_exceeded_routes_to_force_final_answer / test_under_limit_continues_reasoning / test_under_limit_with_native_tools`; idempotence pinned by the `is_finished` early-return in `ensure_force_final_answer` (`agent_executor.py:1389-1411`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "enforce_rpm_limit has_reached_max_iterations force final answer", limit: 6, detail: "ids" });
```

## Verdict
Adopt pre-call throttling through an injectable closure + degrade-don't-die iteration cap; adapt the sleep-based window to a token-bucket if you need smooth rates; omit nothing else — both guards are small and load-bearing.
