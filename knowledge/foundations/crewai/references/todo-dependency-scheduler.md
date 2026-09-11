<!-- capsule-v2 -->
# Todo dependency scheduler — when do steps run sequentially vs in parallel, and what unblocks a failed dependency?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What makes a todo "ready", why is a failed dependency terminal-not-blocking, and how does the executor pick the single-vs-parallel path?

## TodoList.get_ready_todos + get_ready_todos_method
**Path/Symbol:** `lib/crewai/src/crewai/utilities/planning_types.py:112-154` (`_dependencies_satisfied`, `get_ready_todos`, `can_parallelize`, `replace_pending_todos`); routing in `experimental/agent_executor.py:1068-1101` (`get_ready_todos_method`), execution at `:1103-1170` (sequential) and `:1220-1354` (parallel).
**Signature:** `def _dependencies_satisfied(self, item: TodoItem) -> bool  # every dep in {"completed","failed"}`; `def replace_pending_todos(self, new_items: list[TodoItem]) -> None`.
**Data Shape:** `TodoItem{id, step_number, description, tool_to_use, status: "pending"|"running"|"completed"|"failed", depends_on: list[int], result}`. `is_complete` = non-empty AND all statuses terminal (completed OR failed).

### Decisive source
```python
def _dependencies_satisfied(self, item: TodoItem) -> bool:
    for dep_num in item.depends_on:
        dep = self.get_by_step_number(dep_num)
        if dep is None or dep.status not in ("completed", "failed"):
            return False
    return True
# docstring: "A dependency is satisfied when it has finished executing — either
# successfully (completed) or not (failed). This prevents downstream todos from
# being permanently blocked when a dependency fails."

# get_ready_todos_method — stuck-state escape hatch:
if not ready:
    if self.state.todos.is_complete:
        return "all_todos_complete"
    self.state.last_replan_reason = (
        "No todos are ready but plan is not complete — "
        "likely a dependency deadlock or missing completion")
    return "needs_replan"
if len(ready) == 1: return "single_todo_ready"
return "multiple_todos_ready"
```

**Flow:** Ready todos of length 1 → `_mark_todo_running(ready[0])` → StepExecutor path (planning enabled) or legacy ReAct injection. Length ≥2 → parallel: mark ALL running, per todo build a frozen `StepExecutionContext(task_description, task_goal, {step_number→result})`, run each via `asyncio.to_thread(step_executor.execute, …)` under `asyncio.gather(return_exceptions=True)`, zip results back positionally (`for todo, item in zip(ready, gathered, strict=True)`), mark failed on exception, then observe each result SEQUENTIALLY (observations mutate shared state). Replans call `replace_pending_todos(new)` which preserves completed/failed/running items and replaces only pending ones.
**Invariant:** Dependency satisfaction is TERMINAL-based, not success-based — requiring `completed` would deadlock every plan after one step failure; the observer decides skip/replan instead. Parallel branches must never share the LLM message list: context crosses ONLY as final result strings inside frozen dataclasses ("No LLM message history, no execution traces, no shared mutable state").
**Probe:** `tests/agents/test_agent_executor.py::TestDependencyResolutionWithFailures.test_failed_dep_unblocks_downstream / test_is_complete_with_mixed_terminal_states / test_pending_todo_ready_when_dep_failed`; parallel path pinned by `test_reasoning_effort_high_runs_full_observation_pipeline`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "TodoList get_ready_todos replace_pending", limit: 5, detail: "ids" });
```

## Verdict
Adopt terminal-status dependency gating and the frozen-context/frozen-result boundary between orchestrator and step worker; adapt the parallelism primitive (threads vs asyncio) to your host; omit crewAI's legacy `_inject_todo_context` ReAct fallback once your planner always produces structured steps.
