<!-- capsule-v2 -->
# Executor flow state — how does one AgentExecutor instance reset between runs without losing its identity?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** Where does an executor keep its mutable conversation/iteration state, and exactly which fields must a fresh run clear?

## AgentExecutorState + invoke() reset ritual
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:135-170` (`class AgentExecutorState`), reset in `invoke` (`:2830-2845`) and mirrored in `_prepare_feedback_iteration` (`:3256-3272`).
**Signature:** `class AgentExecutor(Flow[AgentExecutorState], BaseAgentExecutor)` — state fields live on `self.state` (a Pydantic model), NOT on the executor instance.
**Data Shape:** State carries both ReAct iteration state (`messages`, `iterations`, `current_answer`, `is_finished`, `ask_for_human_input`, `use_native_tools`, `pending_tool_calls`) AND Plan-and-Execute state (`plan`, `plan_ready`, `todos`, `replan_count`, `last_replan_reason`, `observations`, `execution_log`). `execution_log` is an audit trail explicitly "NOT used for LLM calls".

### Decisive source
```python
# invoke(): reset state for fresh execution — every field, every time
self._finalize_called = False          # PrivateAttr, outside state
self.state.messages.clear()
self.state.iterations = 0
self.state.current_answer = None
self.state.is_finished = False
self.state.use_native_tools = False
self.state.pending_tool_calls = []
self.state.plan = None
self.state.plan_ready = False
self.state.todos = TodoList()
self.state.replan_count = 0
self.state.last_replan_reason = None
self.state.observations = {}
self.state.execution_log = []
# then: if self.llm is None or self.prompt is None: raise RuntimeError(
#     "AgentExecutor.llm or .prompt is unset; the executor was "
#     "not fully restored or initialized before execution.")
```

**Flow:** `invoke(inputs)` → acquire `_execution_lock`, raise `RuntimeError("Executor is already running…")` if `_is_executing` already set → set `_is_executing=True` under the lock, release → full state reset → `_setup_messages` → inject files → `kickoff()` (the Flow engine) → read `state.current_answer` → require `AgentFinish` else `RuntimeError("Agent execution ended without reaching a final answer.")` → optional human-feedback loop → `_save_to_memory` → return `{"output": …}` → `finally: self._is_executing = False`.
**Invariant:** A porter who stores messages on the executor instead of in a resettable state object breaks human feedback (which reruns the WHOLE flow with `_prepare_feedback_iteration()` while KEEPING prior `state.messages`) and double-invocation protection. The lock check-and-set must happen atomically under `_execution_lock`; the reset happens OUTSIDE it so long runs don't hold the lock.
**Probe:** `lib/crewai/tests/agents/test_agent_executor.py::TestExecutorStateReset` (pins `_finalize_called` reset in BOTH `invoke` and `invoke_async`; also pins the unset-llm/prompt RuntimeError path).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "AgentExecutorState invoke reset", limit: 5, detail: "ids" });
// → AgentExecutorState Class …/experimental/agent_executor.py 135-170; TestExecutorStateReset tests
```

## Verdict
Adopt the state-object-plus-reset-ritual shape and the atomic busy-lock (works for any Flow-driven executor); adapt field lists to your own state model; omit crewAI's Pydantic `exclude=True` field plumbing and the `Flow[AgentExecutorState]` multiple inheritance (any orchestrator works). No coverage caveat beyond the repo-wide best-effort note — all cited paths `no_recorded_issue`.
