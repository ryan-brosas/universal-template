<!-- capsule-v2 -->
# write_todos (stateless tool, stateful agent field)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** Where does the in-loop task list live so a shared registry-wide Tool instance can update it safely?

## Path/Symbol
`tools/builtin/planning/todos.py` — `WriteTodosTool.handle()` (:66–77). List lives on the calling `Agent` instance (`agent.todos`, part of the AgentHandle surface); the tool object itself is STATELESS (:12–25).

## Signature
`handle()`: `agent.todos = [t if isinstance(t, Todo) else Todo(**t) for t in raw_todos]` then observability writes + timeline append; returns `{"count": len(agent.todos)}`.

## Data Shape
Arg `todos`: FULL replacement list of `{content: str, status: 'pending'|'in_progress'|'completed'}`. The tool description mandates: ALWAYS pass the complete list (REPLACE, not append), exactly one item in_progress at a time, mark completed immediately — because the list is shown back to the model every turn.

### Decisive source
```python
agent = ctx.agent
raw_todos = call.arguments.get("todos", [])
agent.todos = [t if isinstance(t, Todo) else Todo(**t) for t in raw_todos]
```

**Flow:** model calls write_todos with the whole list → agent field replaced → obs.write_state + timeline record → next turns render the list back into context. replan's handle reads the same field as prior-plan text (`"\n".join(f"- {t.content}" for t in agent.todos)` — replan.py :64), closing the loop: todos are the mutable plan, replan regenerates them.

**Invariant:** Tool instances are shared across the WHOLE registry (stateless by design); all per-run mutability goes through `ctx.agent` (the same split fetch_tools/list_toolsets use for visibility state). Full-replace semantics (never diff/append) keeps list state derivable from one call.

**Probe:** No direct unit test for the tool (coverage caveat): todos capture/restore is pinned at checkpoint level by tests/unit/agent_loop_lib/agent/test_phase_driver.py and run-resume tests (todos ride AgentCheckpoint).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["WriteTodosTool","agent.todos","replan"]'
```

## Verdict
Adopt full-replace todo semantics + stateless-tool/stateful-agent split; adapt where the list lives (any per-run store works if it rides checkpoints).
