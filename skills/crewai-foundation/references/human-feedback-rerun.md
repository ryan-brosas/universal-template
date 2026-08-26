<!-- capsule-v2 -->
# Human-feedback rerun — how does feedback loop the WHOLE flow while preserving conversation, and skip re-planning?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** After `ask_for_human_input`, how is the executor re-run with the user's feedback and what state must be reset vs retained?

## _handle_human_feedback / _prepare_feedback_iteration / _invoke_loop
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:3213-3248` (feedback handlers), `:3249-3254` (`_complete_feedback`), `:3256-3272` (`_prepare_feedback_iteration`), `:3273-3297` (`_invoke_loop`/`_ainvoke_loop`); provider protocol `core/providers/human_input.py:59-164`.
**Signature:** `def invoke(self, inputs) -> dict | Coroutine  # magic auto-async: is_inside_event_loop() → returns self.invoke_async(inputs)`; provider hook `setup_messages(context) -> bool` may OWN message setup entirely.
**Data Shape:** Provider protocol `HumanInputProvider`: `setup_messages`, `post_setup_messages`, `handle_feedback(formatted_answer, context) -> AgentFinish`, `handle_feedback_async`. `_is_feedback_iteration: PrivateAttr[bool]`.

### Decisive source
```python
def _prepare_feedback_iteration(self) -> None:
    """Reset flow completion state before rerunning with feedback."""
    self._finalize_called = False
    self._is_feedback_iteration = True     # generate_plan checks this FIRST
    self.state.current_answer = None
    self.state.is_finished = False
    self.state.iterations = 0
    ...todos/replan/observations/execution_log cleared...
    # NOTE: state.messages is NOT cleared — the feedback continues the thread

def _invoke_loop(self) -> AgentFinish:
    self._prepare_feedback_iteration()
    try:
        self.kickoff()                     # reruns the whole Flow graph
    finally:
        self._is_feedback_iteration = False
```

**Flow:** invoke end: if `state.ask_for_human_input` → `_handle_human_feedback(AgentFinish)` → provider prompts the user (sync stdin or async channel), loops until satisfied; a dissatisfied review appends feedback to the KEPT messages and calls `_invoke_loop`, which resets completion flags but not history and reruns `generate_plan → … → finalize`; the new answer replaces current_answer; `_complete_feedback` then sets `is_finished=True` AND `_finalize_called=True` so any in-flight finalize trigger becomes a no-op. Entry guard: `generate_plan` returns immediately when `_is_feedback_iteration` (test: `test_feedback_iteration_skips_plan_generation`) — no fresh plan on a feedback pass.
**Invariant:** The reset list is deliberately NARROWER than invoke's: messages persist (that's the point of feedback), everything else resets. Forgetting `_finalize_called=False` makes the rerun's finalize silently return "completed" without setting an answer; forgetting `_complete_feedback`'s `_finalize_called=True` lets a stale trigger overwrite the reviewed answer. The provider can also hijack setup via `setup_messages → True` (used for conversation resumption).
**Probe:** `tests/agents/test_agent_executor.py::test_human_feedback_reruns_flow_with_state_messages`, `test_async_human_feedback_reruns_flow_with_state_messages`, `test_feedback_iteration_skips_plan_generation`, `test_setup_messages_calls_human_input_provider_hooks`, `test_setup_messages_can_be_owned_by_human_input_provider`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "human feedback invoke_async executor", limit: 6, detail: "ids" });
```

## Verdict
Adopt preserve-history rerun with narrow reset + double-flag finalization control; adapt the provider protocol to your chat frontend (Slack/web providers implement the same four methods); omit the sync-provider stdin default entirely for server hosts.
