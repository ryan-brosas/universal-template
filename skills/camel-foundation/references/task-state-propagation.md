<!-- capsule-v2 -->
# Recursive state propagation — How does marking one task DONE or RUNNING cascade through the task tree?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What are the exact recursion rules of Task.set_state, and what is the surprising default state?

## Asymmetric recursion: DONE fans down, RUNNING bubbles up
**Path/Symbol:** `camel/tasks/task.py:Task.set_state` (:336-348), defaults (:252-284).
**Signature:** `def set_state(self, state: TaskState) -> None`; `TaskState = str Enum {OPEN, RUNNING, DONE, FAILED, DELETED}`.
**Data Shape:** Pydantic `Task` model; NOTE the field default: `state: TaskState = TaskState.FAILED` (with upstream TODO "Add logic for OPEN in workforce.py") — a freshly constructed Task is FAILED until explicitly set.

### Decisive source
```python
self.state = state
if state == TaskState.DONE:
    for subtask in self.subtasks:
        if subtask.state != TaskState.DELETED:
            subtask.set_state(state)          # fan DOWN, skip deleted
elif state == TaskState.RUNNING and self.parent:
    self.parent.set_state(state)              # bubble UP
```

**Flow:** DONE marks the node and recursively every non-DELETED descendant → RUNNING climbs to the root so ancestors reflect activity → FAILED/OPEN/DELETED set only the node itself. Related tree walks follow the same shape: `get_running_task()` descends depth-first returning the first RUNNING leaf-or-self; `update_result(result)` sets result then `set_state(DONE)` (triggering the downward fan); `reset()` restores the FAILED default and clears result.
**Invariant:** The DELETED guard inside the DONE fan is load-bearing — completing a parent must not resurrect deleted subtasks; and because RUNNING recurses upward through `parent`, a cycle-free tree is required (`add_subtask` sets `task.parent = self`, so re-parenting mid-flight can corrupt walks).
**Probe:** `grep -n 'TaskState.FAILED\n    )' camel/tasks/task.py | head -2` returns nothing (multiline); use `python3 - <<'EOF'
src=open('camel/tasks/task.py').read()
print(src.count('state: TaskState = (\n        TaskState.FAILED'), src.count('subtask.state != TaskState.DELETED'))
EOF` → `1 1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "Task set_state subtasks DELETED parent RUNNING", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the asymmetric recursion for hierarchical work items; keep the explicit DELETED exemption. Adapt enum values. Omit media fields (image_list/video_bytes) — payload sugar, not semantics.
