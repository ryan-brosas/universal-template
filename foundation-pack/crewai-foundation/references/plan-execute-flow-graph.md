<!-- capsule-v2 -->
# Plan-and-Execute flow graph — how do @start/@router labels wire a supervisor loop that cannot fall through?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How is the whole agent execution expressed as a Flow event graph, and which label transitions form the loop?

## Method-label router chain
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:347` (`@start generate_plan`), `:643-2440` (routers), `:2331-2339` (`finalize` listener).
**Signature:** `def method(self) -> Literal["label_a", "label_b"]` under `@router("incoming_label")`, `@router(other_method)` (method-reference = the OTHER method's returned label), or `@router(or_("a", "b"))`.
**Data Shape:** Every transition is a string label; routers return `Literal[...]` so typos are type errors. The engine (`crewai/flow/runtime/__init__.py`) matches each emitted event against registered conditions via `_condition_met` (pending-event set per subscription, cleared on satisfaction) with a per-listener `_method_call_counts` RecursionError guard at `max_method_calls` (executor sets `max_method_calls = max_iter * 10` in `_setup_executor`).

### Decisive source
```python
@router(or_(initialize_reasoning, continue_iteration))
def check_max_iterations(self) -> Literal[
    "force_final_answer", "continue_reasoning", "continue_reasoning_native"
]:
    if has_reached_max_iterations(self.state.iterations, self.max_iter):
        return "force_final_answer"          # one more LLM call demanding Final Answer
    if self.state.use_native_tools:
        return "continue_reasoning_native"
    return "continue_reasoning"

@router("parser_error")
def recover_from_parser_error(self) -> Literal["initialized"]: ...   # loops back
@router("context_error")
def recover_from_context_length(self) -> Literal["initialized"]: ...  # loops back

@listen(
    or_("all_todos_complete", "agent_finished",
        "tool_result_is_final", "native_finished")
)
def finalize(self) -> Literal["completed", "skipped"]: ...
```

**Flow:** `generate_plan` (@start) → `check_todos_available` → {`has_todos` | `no_todos` | `planning_disabled`} → todo branch: `get_ready_todos_method` → single → `execute_todo_sequential` → `step_executed` → `observe_step_result` → low/medium/high handlers → … → `all_todos_complete`; non-todo branch: `initialize_reasoning` → `initialized` → `check_max_iterations` → ReAct loop (`call_llm_and_parse` → `route_by_answer_type` → `execute_tool_action` → `check_todo_completion` → satisfied/not → back to `initialized`) or native loop (`call_llm_native_tools` → `execute_native_tool` → `check_native_todo_completion`) → any of four finish labels → `finalize`. Error edges: `parser_error`/`context_error` both re-enter `initialized` after recovery.
**Invariant:** EVERY terminal route must land on one of finalize's four listened labels; a new exit path that emits an unlistened label hangs the run. The `or_()` listeners plus `_condition_met`'s pending-set semantics mean two different methods emitting the same label in ONE pass still trigger the listener exactly once — but the framework can deliver a label twice across passes, hence the idempotence guards inside handlers (`ensure_force_final_answer` checks `is_finished`; see its comment about "both initialize_reasoning and increment_and_continue" emitting `initialized`).
**Probe:** `lib/crewai/tests/agents/test_agent_executor.py::test_exceeded_routes_to_force_final_answer / test_under_limit_continues_reasoning / test_under_limit_with_native_tools` (pin the three-way routing decision).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "AgentExecutor finalize replan todos", limit: 8, detail: "ids" });
// → AgentExecutor.finalize 2339-2411; handle_replan_now; check_max_iterations …
```

## Verdict
Adopt the label-router-graph pattern for any multi-phase agent loop — it makes every control edge inspectable and testable in isolation; adapt label vocabulary to your state machine; omit crewAI's decorator reflection machinery (`flow/dsl`, `flow/runtime` ~3.9kL) if your host already has a scheduler.
