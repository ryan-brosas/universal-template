<!-- capsule-v2 -->
# PlannerNode browser router — which four next-agents exist, why is one edge self-looping, and what resets navigation paths?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the browser planner map LLM-chosen next agents onto graph edges, and where do conclude/memorize detours write subtask history?

## Router-map-with-a-twist over NextAgentPlan
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/browser/browser_planner.py:PLANNER_ROUTER_MAP` (:20-25), `PlannerNode.node_handler` (:38-91).
**Signature:** `node_handler(state, agent, name) -> Command[Literal["ActionAgent","QaAgent","PlanControllerAgent","BrowserPlannerAgent"]]`.
**Data Shape:** `NextAgentPlan{next_agent: str, instruction: str, ...}` (browser prompts/load_prompt.py :33-39); step log entries appended to `stm_steps_history` carry `(AgentName): instruction` prefixes.

### Decisive source
```python
PLANNER_ROUTER_MAP = {
    "ConcludeTaskAgent": "PlanControllerAgent",
    "QaAgent": "QaAgent",
    "MemorizeAgent": "BrowserPlannerAgent",
    "ActionAgent": "ActionAgent",
}
...
        elif next_step_plan.next_agent == "MemorizeAgent":
            state.last_planner_answer = next_instruction
            state.stm_steps_history.append("(MemorizeAgent): " + next_instruction)
            return Command(update=state.model_dump(), goto="BrowserPlannerAgent")
```
and the counter reset:
```python
        if tracker.actions_count >= 4:
            logger.debug("Resetting navigation paths")
            state.task_analyzer_output.navigation_paths = None
```

**Flow:** actions_count ≥ 4 ⇒ navigation paths cleared BEFORE planning (forces fresh approaches instead of replaying exhausted ones). Plan recorded (tracker step with `image_before` + `observation_before`), `state.plan/plan_next_agent/next_step/previous_steps` updated. ConcludeTaskAgent ⇒ append SubTaskHistory(sub_task, steps=[all instructions], final_answer=instruction) + `last_planner_answer` → PlanControllerAgent; MemorizeAgent ⇒ record answer then SELF-LOOP back to the planner (memory step is invisible to routing); QaAgent ⇒ just logs `(QaAgent): …` and falls through to dynamic goto; unknown name ⇒ `raise Exception("Unhandled agent")` (fail loud, NOT a silent edge).
**Invariant:** PLANNER_ROUTER_MAP documents the mapping but the handler's if/elif chain is authoritative — MemorizeAgent routes BACK to the planner itself, not to a distinct node; porters who build edges purely from the dict add a phantom node. The fallthrough goto uses the RAW next_agent string, so QaAgent/ActionAgent must equal real node names.
**Probe:** Recorded upstream gap (router has no dedicated unit test). Deterministic: `sed -n '20,25p' src/cuga/backend/cuga_graph/nodes/browser/browser_planner.py` matches the map above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "PLANNER_ROUTER_MAP NextAgentPlan PlannerNode browser", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt LLM-named next-agent routing validated against static edges with fail-loud unknown handling, the self-loop memory detour, and activity-count navigation resets. Adapt the agent vocabulary. Omit the QA/memorize nodes you don't carry — but keep SOME terminal for conclude.
