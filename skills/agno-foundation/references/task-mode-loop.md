<!-- capsule-v2 -->
# Task-mode supervisor loop — how does the leader drive an autonomous plan to completion without spinning forever?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What terminates the iterative plan→delegate→observe loop, and what does each iteration inject?

## Iterative task loop `_arun_tasks`
**Path/Symbol:** `libs/agno/agno/team/_run.py:2062` (`async def _arun_tasks`, loop :2210–2278; sync twin `_run_tasks` :227).
**Signature:** `async def _arun_tasks(team, run_response, run_context, session_id, ...) -> TeamRunOutput` — dispatched from `_arun` when `team.mode == TeamMode.tasks`.
**Data Shape:** shared plan lives in `run_context.session_state["_team_tasks"]` (loaded/saved via `load_task_list`/`save_task_list`, task.py:247-261); leader model receives accumulated message list + injected state summaries.

### Decisive source
```python
for iteration in range(team.max_iterations):          # default 10
    if iteration > 0:
        task_list = load_task_list(run_context.session_state)
        state_message = Message(role="user", content=(
            f"<current_task_state>\n{task_summary}\n</current_task_state>\n\n"
            "Continue working on the tasks. Create, execute, or update tasks as needed. "
            "When all tasks are done, call `mark_all_complete` with a summary."))
        accumulated_messages.append(state_message)
    model_response = await acall_model_with_fallback(...)
    ...
    if run_response.requirements and any(not req.is_resolved() for req in run_response.requirements):
        return await _hooks.ahandle_team_run_paused(...)   # HITL pause short-circuits mid-loop
    task_list = load_task_list(run_context.session_state)
    if task_list.goal_complete:
        break
    if task_list.all_terminal():
        has_failures = any(t.status == TaskStatus.failed for t in task_list.tasks)
        if not has_failures:
            break                                          # clean finish
        log_debug("All tasks terminal but some failed, continuing to let model handle.")
else:
    if not task_list.goal_complete:
        log_warning(f"Reached max_iterations ({team.max_iterations}) without completing all tasks.")
```

**Flow:** per iteration: inject `<current_task_state>` summary as a user message → model call → HITL-pause check (unresolved requirements pause the WHOLE team) → re-load plan from session_state → exit on `goal_complete` OR all-terminal-without-failures; failures keep the loop alive so the model can recover; exhaustion falls out with only a warning — status still becomes `completed`.
**Invariant:** (1) Termination is dual-keyed: explicit `mark_all_complete` flag OR derived all-terminal-clean; failed tasks deliberately do NOT terminate. (2) The plan is RE-READ from session_state every iteration — tools mutate their own copy; trusting an in-memory snapshot would miss tool-written updates. (3) `max_iterations` exhaustion is not an error.
**Probe:** `tests/integration/teams/test_tasks_mode_streaming.py::test_tasks_mode_goal_complete_in_state_event` (:272-308); graph-resolves line-exact via search_graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_arun_tasks max_iterations goal_complete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual termination keys and the per-iteration state-summary injection; adapt the summary tag names and iteration default; omit agno's specific `<current_task_state>` prompt wording if your host has its own protocol. Caveat: streaming twin `_arun_tasks_stream` (:2418) shares semantics plus event emission.
