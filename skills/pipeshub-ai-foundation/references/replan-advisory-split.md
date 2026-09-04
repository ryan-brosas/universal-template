<!-- capsule-v2 -->
# replan (goal-text augmentation, not plan mutation)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What exactly does the replan tool feed its Replanner — and what does it deliberately NOT do?

## Path/Symbol
`tools/builtin/planning/replan.py` — whole file, 87L; `handle()` :51–84. Delegates to `modules/pipeline/planner/replanner.py::Replanner(model=..., prior_plan_text=...)`.

## Signature
```python
prior_plan_text = "\n".join(f"- {t.content}" for t in agent.todos) or None
replan_goal = goal.model_copy(update={
    "description": f"{goal.description}\n\nReplanning reason: {reason}" if reason else goal.description,
})
new_plan = await Replanner(model=model, prior_plan_text=prior_plan_text).plan(replan_goal)
```

## Data Shape
Arg: `reason` (required — why reality diverged). Prior plan rendered from the agent's CURRENT todos as bullet lines (empty ⇒ None). Returns free-form `new_plan.text` verbatim; error string on failure. Observability: write_state + timeline ("Replanned"/"Replan failed") with the reason in metadata.

### Decisive source
```python
tr_content: object = new_plan.text
tr_is_error = False
...
return CoreToolResult(tool_call_id=call.id, name=call.name, content=tr_content, is_error=tr_is_error)
```

**Flow:** todos diverge from reality → replan(reason) → Replanner gets (replan_goal w/ reason appended, prior bullets) → new plan TEXT returned → the MODEL must follow up with write_todos to actually mutate the task list (enforced by the tool description's "Follow up with write_todos").

**Invariant:** replan NEVER mutates state itself — no slot write, no todos rewrite, no STRUCTURED_PLAN_SLOT update. It's a pure read-todos→LLM→text advisory; the write side stays exclusively with write_todos. The reason rides INSIDE the goal copy (`model_copy(update=...)`) so the original Goal is untouched. Model resolution uses the same swallow-to-None transport_registry ladder as every planning tool.

**Probe:** No dedicated unit test (coverage caveat): Replanner internals exercised via tests/unit/agent_loop_lib/agent/test_plan_execute_loop.py (pinned-plan loop family); this file adds only the todo-rendering + goal-augmentation contract, verified by source inspection.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["ReplanTool","Replanner","prior_plan_text"]'
```

## Verdict
Adopt the advisory-replan/read-write split (replan reads+proposes, write_todos commits); adapt Replanner interface.
