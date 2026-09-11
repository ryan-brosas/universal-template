<!-- capsule-v2 -->
# PlanControllerNode — sub-task router with single-step bypass and synthetic-message history discipline

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A decomposed multi-step task needs a controller that picks the next sub-task and its executor (web vs API). How do you keep single-step tasks from paying controller-LLM cost on EVERY turn, and how do you keep the message history uniform when logic (not the LLM) makes the decision?

## The router
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/plan_controller.py` (`PlanControllerNode.node_handler` :54-288, single-step bypass :65-68/:97-159, loop-return shortcut :164-179, open-app special case :195-208).
**Signature:** `async node_handler(state, agent, name, config) -> Command[Literal["BrowserPlannerAgent","APIPlannerAgent","FinalAnswerAgent","PlanControllerAgent","InterruptToolNode"]]`.
**Data Shape:** decisions arrive as `PlanControllerOutput` JSON in an AIMessage (thoughts / next_subtask / subtasks_progress / conclude_task / conclude_final_answer / next_subtask_app / next_subtask_type).

### Decisive source
```python
# plan_controller.py:65-68 — the bypass predicate
ignore_controller = (
    len(state.task_decomposition.task_decomposition) == 1
    or len(state.task_decomposition.task_decomposition) == 0
)

# :142-154 — logic-made decisions still enter history AS IF the model chose
state.messages.append(
    AIMessage(content=PlanControllerOutput(thoughts=[], next_subtask=state.sub_task,
        subtasks_progress=[], conclude_task=False, ...).model_dump_json()))

# :188-193 — two completion signals, either ends the task
if plan_controller_output.conclude_task or (
    all(status == "completed" for status in plan_controller_output.subtasks_progress)
    and plan_controller_output.next_subtask == ""):
    state.last_planner_answer = plan_controller_output.conclude_final_answer
    return Command(update=state.model_dump(), goto="FinalAnswerAgent")
```

**Flow:** arrival-from-decomposer path: force configured lite apps into relevant apps, then if `ignore_controller`, copy step 0 into `sub_task/sub_task_app/sub_task_type` and dispatch directly — NO LLM call. Loop-return path (sender is a planner): if single-step AND a planner answer exists, conclude immediately using it (`conclude_task=True` synthetic message → FinalAnswerAgent) — a one-subtask task never re-enters the controller LLM. Multi-step: `agent.run` parses real output; conclusion check above; else an "open application" sub-task short-circuits to a synthesized `open_app` tool_call plus a pre-filled `SubTaskHistory("Navigated to {app}")` routed through InterruptToolNode; API-targeted sub-tasks clear chat messages, REQUIRE `next_subtask_app` (empty app = ValueError, schema violation fails loudly), filter `api_intent_relevant_apps_current` to that app, and refresh filtered APIs unless the app is a forced-lite app. Every exit is `Command(update=state.model_dump(), goto=...)`.
**Invariant:** the controller NEVER lets an LLM see a trivial routing decision (both directions of the single-step bypass are LLM-free); every decision — model-made or logic-made — lands in `state.messages` as a serialized `PlanControllerOutput` so downstream prompt renderers see one uniform history shape; `state.sender` is set to self BEFORE dispatch so the loop-return path is distinguishable from first arrival.

**Probe:** direct tests `tests/unit/test_plan_controller_prompt.py::test_infinite_loop_prevention_scenario` (:255), `::test_stm_history_with_final_answer` (:29), `::test_stm_history_empty` (:80), `::test_cuga_lite_node_empty_steps_pattern` (:302) — prompt-rendering pins for the history contract above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "PlanControllerNode ignore_controller conclude_task next_subtask InterruptToolNode", limit: 10 });
```

## Verdict
Adopt the single-step bypass (never pay controller cost twice for a trivial plan), synthetic-decision-message history uniformity, loud schema-violation errors for missing routing fields, and full-state Command handoffs. Adapt the executor literals (browser/API planners) and the open-app special case to your tool surface. Omit AppWorld-specific app-name substrings.
