<!-- capsule-v2 -->
# Task-list FSM — how do blocked tasks and failed dependencies cascade so the supervisor loop cannot deadlock?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** When a dependency fails, what must happen to its dependents for `all_terminal()` to remain a sound loop-exit condition?

## TaskList status recomputation
**Path/Symbol:** `libs/agno/agno/team/task.py:206` (`TaskList._update_blocked_statuses`, with `_is_blocked` :184, `TERMINAL_STATUSES`/`DEPENDENCY_SATISFIED_STATUSES` :74-75).
**Signature:** `_update_blocked_statuses(self) -> None` — called after EVERY mutation (`create_task`, `update_task`, `from_dict`).
**Data Shape:** five-state FSM per task (`pending → in_progress → completed|failed`, plus `blocked`); dependencies are lists of task-id strings; unknown ids are legal input.

### Decisive source
```python
DEPENDENCY_SATISFIED_STATUSES = {TaskStatus.completed}

def _is_blocked(self, task) -> bool:
    for dep_id in task.dependencies:
        dep = self.get_task(dep_id)
        if dep is None:
            return True  # Unknown dependency ID -- treat as blocked (fail-closed)
        if dep.status not in DEPENDENCY_SATISFIED_STATUSES:
            return True
    return False

def _update_blocked_statuses(self) -> None:
    for task in self.tasks:
        if task.status == TaskStatus.blocked:
            if self._has_failed_dependency(task):
                task.status = TaskStatus.failed
                task.result = "Automatically failed: a dependency failed."
            elif not self._is_blocked(task):
                task.status = TaskStatus.pending
        elif task.status == TaskStatus.pending:
            if self._is_blocked(task):
                task.status = TaskStatus.blocked
```

**Flow:** any mutation → recompute every pending/blocked task: failed dependency ⇒ dependent auto-fails (transitively, because each recomputation pass sees the new failure); satisfied deps ⇒ blocked→pending; unsatisfied ⇒ pending→blocked.
**Invariant:** (1) ONLY the auto-cascade writes the explanatory result string — manual `update_task(status="failed")` never fabricates one (probed live). (2) The auto-fail cascade is what keeps `all_terminal()` (all tasks ∈ {completed, failed}) true after any single failure — without it, a chain rooted at a failed task would hang the task-mode loop until `max_iterations`. (3) Unknown dependency ids fail CLOSED to blocked, never silently satisfiable.
**Probe:** `tests/unit/team/test_task_model.py::test_dependency_blocks_task / test_completing_dependency_unblocks / test_multiple_dependencies`; live-executed at pin: unblock-on-complete ✓, unknown-dep fail-closed ✓, transitive b,c auto-fail + `all_terminal() is True` ✓.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "TaskList._update_blocked_statuses", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-closed unknown-dependency rule and the auto-fail cascade as a pair — they are jointly load-bearing for loop termination; adapt state names/result strings; omit agno's session_state serialization key (`_team_tasks`) if your host stores plans elsewhere. Direct tests exist and were executed green.
