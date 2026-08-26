<!-- capsule-v2 -->
# TaskManager topological ledger — How do you keep an ordered task list and id map consistent as tasks are added out of order?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** Why does add_tasks re-sort the whole list topologically, and what does the serial/parallel dependence helper guarantee?

## Sort-on-insert + DFS post-order
**Path/Symbol:** `camel/tasks/task.py:TaskManager` (:627-729), `topological_sort` (:659-688), `set_tasks_dependence` (:690-718).
**Signature:** `add_tasks(tasks: Union[Task, List[Task]]) -> None`; `gen_task_id() -> str` = `f"{len(self.tasks)}"`; `static topological_sort(tasks) -> List[Task]`.
**Data Shape:** `tasks: List[Task]` (execution order), `task_map: Dict[str, Task]`, `current_task_id`; duplicate ids assert-fail (`assert not self.exist(task.id)`).

### Decisive source
```python
def visit(task: Task):
    if task.id in visited:
        return
    visited.add(task.id)
    for sub_task in task.subtasks:
        visit(sub_task)
    stack.append(task)      # children before parents

for task in tasks:
    visit(task)
return stack
```

**Flow:** every insertion re-runs the DFS post-order over the FULL list so dependencies always precede dependents in `self.tasks`, then rebuilds `task_map` from the sorted order — O(n log n)-ish per add but immune to incremental-order bugs. `set_tasks_dependence(root, others, "serial"|"parallel")` chains subtasks root→o1→o2 or fans root→each, filtering `other != root` first (self-loop guard). `evolve(task, agent)` regenerates a harder variant of one task for datagen and returns its first parsed successor or None.
**Invariant:** The visited-set makes cycles terminate (though they yield wrong orders silently — cycle freedom is assumed, matching Task.parent discipline); ids are positional strings ("0", "0.1") for decomposed trees but uuid4 by default on bare Tasks.
**Probe:** `grep -c 'topological_sort' camel/tasks/task.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "TaskManager topological_sort set_tasks_dependence add_tasks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sort-on-insert ledger for small hierarchical plans; adapt to persistent storage at scale. Omit evolve/compose LLM helpers unless porting datagen flows.
