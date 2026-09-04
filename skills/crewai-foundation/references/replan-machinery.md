<!-- capsule-v2 -->
# Replan machinery — when does the plan regenerate, what does it preserve, and why is the counter incremented by the caller?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What are the exact replan triggers and limits, and how is completed work preserved across a replan?

## _should_replan / handle_replan_now / handle_replan / _trigger_replan
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:2537-2587` (`_should_replan`), `:1011-1051` (`handle_replan_now`, Plan-and-Execute edge), `:2738-2761` (`handle_replan`, legacy edge), `:2589-2674` (`_trigger_replan`).
**Signature:** `def _should_replan(self) -> tuple[bool, str]`; `def _trigger_replan(self, reason: str) -> None` — "NOTE: Callers are responsible for incrementing ``replan_count`` before calling this method".
**Data Shape:** Triggers: ≥2 failed todos; ≥2 todos whose result starts `"Error:"`; OR the last message content containing any of six lowercase indicators: `need to reconsider` / `approach isn't working` / `try a different approach` / `replan` / `revise the plan` / `plan needs adjustment`. Limit: `replan_count >= max_replans` (config default 3).

### Decisive source
```python
if self.state.replan_count >= max_replans:
    if self.agent.verbose:
        PRINTER.print(content=f"Max replans ({max_replans}) reached — "
                              "finalizing with current results", color="yellow")
    return "all_todos_complete"        # degrade to finalize, never hang
self.state.replan_count += 1           # caller-side increment (handle_replan_now)
...
self._trigger_replan(reason)           # regenerates plan via AgentReasoning
# inside _trigger_replan: task.description is saved and RESTORED around the
# planning call (shared object — mutation would accumulate on re-invoke);
# for kickoff path description is read-only → a NEW AgentReasoning is built.
self.state.plan = output.plan.plan; self.state.plan_ready = output.plan.ready
if self.state.plan_ready and output.plan.steps:
    new_todos = [TodoItem(step_number=step.step_number,
                          description=step.description,
                          tool_to_use=step.tool_to_use,
                          depends_on=step.depends_on) ...]
    self.state.todos.replace_pending_todos(new_todos)
    # ^ preserves completed/failed/running history for context + synthesis
```

**Flow:** Any router reaching `needs_replan`/`replan_now` → guard check → emit `PlanReplanTriggeredEvent` (carrying `completed_steps_preserved`) → `_trigger_replan` builds `_build_replan_context()` from execution log + observations, enhances the task description with previous-attempt context, calls `AgentReasoning.handle_agent_reasoning()`, swaps pending todos → route back to `has_todos` (or finalize if nothing pending). Two entry points exist because Plan-and-Execute (`handle_replan_now`) must return todo labels while the legacy loop's `handle_replan` returns `no_todos` → `initialize_reasoning`.
**Invariant:** Completed results survive every replan (`replace_pending_todos` only touches pending items); new step numbers may collide with old ones but `get_by_step_number` scans current items only. The counter guard lives in EACH handler (not inside `_trigger_replan`) because each flow method needs its own early-exit label. A porter centralizing the increment in the trigger will double-count or skip the max-replan finalization path.
**Probe:** `tests/agents/test_agent_executor.py::test_generate_plan_does_not_mutate_task_description`; replan routing pinned by `test_reasoning_effort_medium_replans_on_failure` and low-effort `replan_now` assertions in `TestReasoningEffort*`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_should_replan _trigger_replan replan", limit: 6, detail: "ids" });
```

## Verdict
Adopt preserve-completed replanning with caller-owned counters and description save/restore; adapt trigger heuristics (the six string indicators are English-prompt-tuned); omit the dual-entry split if your executor has a single execution mode.
