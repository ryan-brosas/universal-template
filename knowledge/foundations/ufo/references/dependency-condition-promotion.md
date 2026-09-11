<!-- capsule-v2 -->
# Dependency-condition promotion — How does one completed task unlock its dependents, with per-edge conditions?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** When a task finishes (success OR failure), how do dependents get unblocked — including edges that only fire on specific results or errors?

## Edge-condition evaluation + dependency stripping + newly-ready return
**Path/Symbol:** `galaxy/constellation/task_constellation.py:TaskConstellation.mark_task_completed` (:436-481) and `get_ready_tasks` (:279-294).
**Signature:** `def mark_task_completed(self, task_id: str, success: bool, result: Any = None, error: Exception = None) -> List[TaskStar]`.
**Data Shape:** `_dependencies: Dict[str, TaskStarLine]` keyed by edge id; each line exposes `from_task_id`, `to_task_id`, and `evaluate_condition(value)`; the condition receives `result` on success and `error` on failure.

### Decisive source
```python
if task.status == TaskStatus.PENDING:
    task.start_execution()
if success:
    task.complete_with_success(result)
else:
    task.complete_with_failure(error)

newly_ready = []
for dependency in self._dependencies.values():
    if dependency.from_task_id == task_id:
        dependent_task = self._tasks.get(dependency.to_task_id)
        if dependent_task and dependent_task.status == TaskStatus.PENDING:
            if dependency.evaluate_condition(result if success else error):
                dependent_task.remove_dependency(task_id)
                if self._are_dependencies_satisfied(dependent_task.task_id):
                    newly_ready.append(dependent_task)
self.update_state()
```
Readiness re-check at scheduling time:
```python
for task in self._tasks.values():
    if task.is_ready_to_execute:
        # Double-check dependencies are satisfied
        if self._are_dependencies_satisfied(task.task_id):
            ready_tasks.append(task)
ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
```

**Flow:** terminal write first (auto-promoting a PENDING task to RUNNING if it was never started) → scan all edges *outgoing from* the finished task → for each still-PENDING dependent, evaluate that edge's condition against the result-or-error payload → satisfied edges are removed from the dependent's dependency set → fully-satisfied dependents join the returned `newly_ready` list → constellation state recomputed. The scheduler then priority-sorts (higher `priority.value` first).
**Invariant:** promotion is edge-scoped, not blanket: an unmet or unsatisfied edge keeps its dependency registered, so a dependent can wait out multiple predecessors; failure payloads flow into conditions exactly like success payloads, enabling on-failure branches.
**Probe:** callers pin behavior: `_execute_task_with_events` (:603-696) embeds `[t.task_id for t in newly_ready]` in TASK_COMPLETED/TASK_FAILED event data, making promotion observable on the bus; readiness double-check is exercised by `tests/test_constellation_sync_observer.py` fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "mark task completed newly ready dependencies evaluate condition", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt per-edge condition evaluation with dependency stripping and a newly-ready return value (it doubles as your event/notification payload). Adapt the condition vocabulary to your domain (UFO leaves `evaluate_condition` semantics to each TaskStarLine). Omit the private-field auto-start branch if your port enforces start-before-complete upstream.
