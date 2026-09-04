<!-- capsule-v2 -->
# Planning LLM contract — how is the initial plan produced, refined until "ready", and kept out of task descriptions?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What is the create_plan/refine loop, its function schema, and the shared-description mutation trap?

## AgentReasoning.handle_agent_reasoning
**Path/Symbol:** `lib/crewai/src/crewai/utilities/reasoning_handler.py:50-104` (`FUNCTION_SCHEMA`), `:107-186` (class + `_resolve_llm`), `:187-310` (`handle_agent_reasoning`, `_execute_planning`, `_create_initial_plan`, `_refine_plan_if_needed`).
**Signature:** `def handle_agent_reasoning(self) -> AgentReasoningOutput` where `AgentReasoningOutput.plan: ReasoningPlan(plan: str, steps: list[PlanStep], ready: bool)`.
**Data Shape:** `PlanStep(step_number int 1-based, description str, tool_to_use str|None, depends_on list[int])`. Schema `create_reasoning_plan` requires `[plan, steps, ready]`, per-step requires all four fields, `additionalProperties: False`.

### Decisive source
```python
def _resolve_llm(self) -> LLM:
    if self.config.llm is not None:            # planning_config.llm wins…
        if isinstance(self.config.llm, LLM): return self.config.llm
        return cast(LLM, create_llm(self.config.llm))
    return cast(LLM, self.agent.llm)           # …else same LLM for everything

plan, steps, ready = self._create_initial_plan()
#   → supports_function_calling(): _call_with_function(schema) → structured steps
#   → else text prompt path: parse plan+ready; steps = []  ("No structured
#     steps from text parsing")
plan, steps, ready = self._refine_plan_if_needed(plan, steps, ready)
while not ready and (max_attempts is None or attempt < max_attempts):
    attempt += 1 ...                            # bounded refinement loop

# executor-side invariant (generate_plan comment):
# "Do NOT mutate task.description — it's a shared object that accumulates
#  plan text on re-invoke."
```

**Flow:** Emit started event → initial plan (function-calling when supported, else prompt-parse with NO steps) → refine while not ready and under `max_attempts` (each attempt emits its own started/completed events and appends prior-plan feedback) → completed event with plan summary. The executor stores output into `state.plan/steps→todos` (`_create_todos_from_plan`) WITHOUT touching `task.description`; replans go through `_enhance_task_for_replan` which save/restores the description around the planning call.
**Invariant:** Text-parsed planning yields NO steps — so an agent whose planner LLM lacks function calling silently degrades to the legacy todo-injected ReAct mode rather than fabricating step lists; porters must preserve that two-tier behavior or they'll invent dependencies the model never produced. `_get_planning_config` maps legacy `max_reasoning_attempts` onto a fresh `PlanningConfig(max_attempts=…)` for backward compatibility.
**Probe:** `tests/agents/test_agent_executor.py::TestPlanning*` — `test_agent_kickoff_with_planning_stores_plan_in_state`, `test_planning_creates_minimal_steps_for_multi_step_task`, `test_planning_handles_sequential_dependency_task`, `test_generate_plan_does_not_mutate_task_description`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "AgentReasoning handle_agent_reasoning FUNCTION_SCHEMA", limit: 6, detail: "ids" });
```

## Verdict
Adopt the schema-first/text-fallback planning split with bounded refinement; adapt prompts via PlanningConfig's system/plan/refine prompt fields; omit the event emissions if you run headless.
