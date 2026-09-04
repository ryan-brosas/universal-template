<!-- capsule-v2 -->
# Reasoning-effort ladder — how much observation/replan machinery runs per step at low/medium/high?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How does the executor degrade the Plan-and-Act observe→decide pipeline by effort level without losing hard-failure safety?

## observe_step_result → low/medium/high handlers
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:643-708` (`observe_step_result`), `:710-780` (`handle_step_observed_low`), `:783-845` (`handle_step_observed_medium`), `:848-930` (`decide_next_action` = high); defaults in `_get_reasoning_effort` (`:518-530`) and `_should_observe_steps` (`:553-565`).
**Signature:** `def _get_reasoning_effort(self) -> str  # config.reasoning_effort or "medium"`; `PlanningConfig(reasoning_effort="low"|"medium"|"high", observe_steps: bool|None, max_replans:int=3, max_step_iterations:int=15, step_timeout:int|None)`.
**Data Shape:** `StepObservation` (`utilities/planning_types.py:212-278`) fields: `step_completed_successfully`, `key_information_learned`, `remaining_plan_still_valid`, `suggested_refinements: list[StepRefinement] | None`, `needs_full_replan`, `replan_reason`, `goal_already_achieved`. A `field_validator(mode="before")` coerces a single dict refinement into a list because LLMs return one object.

### Decisive source
```python
# low: heuristic only, but hard failures still escalate
if (observation and not observation.step_completed_successfully
        and observation.needs_full_replan):
    self._mark_todo_failed(..., error=observation.replan_reason)
    return "replan_now"
if observation and not observation.step_completed_successfully:
    self._mark_todo_failed(...)   # recorded as failed; loop CONTINUES anyway

# medium (handle_step_observed_medium): LLM observe; replan on failure only
# high (decide_next_action) — full pipeline, ordered:
if observation.goal_already_achieved:      return "goal_achieved"   # early exit
if observation.needs_full_replan:          return "replan_now"
if not observation.step_completed_successfully: return "replan_now"
if observation.remaining_plan_still_valid and observation.suggested_refinements:
                                           return "refine_and_continue"
return "continue_plan"
```

**Flow:** Step finishes → `observe_step_result` stores `StepObservation` in `state.observations[step_number]` + appends an audit entry → routes on effort. Low: no LLM observation (`PlannerObserver.heuristic_observation(step_success=…)`), failed steps are marked failed but never replanned UNLESS `needs_full_replan` is set. Medium: LLM observation; replan only when the step failed. High: goal-achieved early termination, full replan, lightweight refinement of pending descriptions (`observer.apply_refinements` mutates pending todo descriptions in place — no second LLM call), or continue.
**Invariant:** The default MUST be `"medium"` when no config exists ("so that step failures reliably trigger replanning rather than being silently ignored") — while bare `Agent(planning=True)` synthesizes `PlanningConfig(reasoning_effort="low", max_attempts=1)` to bound cost. A porter unifying these two defaults either makes cheap planning expensive or loses failure-driven replanning.
**Probe:** `lib/crewai/tests/agents/test_agent_executor.py::TestReasoningEffort*` — `test_reasoning_effort_low_skips_planner_observer_llm`, `test_reasoning_effort_low_skips_decide_and_replan`, `test_reasoning_effort_high_runs_full_observation_pipeline`, `test_reasoning_effort_medium_replans_on_failure`, `test_low_marks_failed_steps_failed_without_replan`; plus `TestPlanningConfigDefaults.test_planning_config_default_is_medium`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "reasoning_effort PlannerObserver observe step", limit: 6, detail: "ids" });
```

## Verdict
Adopt the three-tier ladder with its "cheap default for bare planning, safe default when unset" split and the low-effort hard-failure escalation; adapt tier thresholds to your latency budget; omit the event-bus emission around each observation if you have no trace UI.
