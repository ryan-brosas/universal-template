<!-- capsule-v2 -->
# PlanController state projection — exactly which five derived views reach the controller prompt, and where does each come from?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does the plan-controller prompt actually receive from AgentState, and which of those inputs have direct rendering tests?

## Five-slot prompt-input assembly
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/plan_controller_agent/plan_controller_agent.py:PlanControllerAgent.run` (:48-90).
**Signature:** `run(input_variables: AgentState) -> AIMessage` via `self.chain.ainvoke(data)`; template pair `./prompts/system.jinja2` + `./prompts/user.jinja2`.
**Data Shape:** slots — `task_decomposition` (rendered list), `stm_all_history` (dumped SubTaskHistory dicts), `sub_tasks_progress`, `variables_history` (manager summary last_n=15), `api_applications_list` (names where type=='api'), plus optional live `img`.

### Decisive source
```python
        task_input = {
            "task_decomposition": input_variables.task_decomposition.format_as_list(),
            "stm_all_history": [item.model_dump() for item in input_variables.stm_all_history]
            if input_variables.stm_all_history
            else [],
        }
        data["variables_history"] = input_variables.variables_manager.get_variables_summary(last_n=15)
        data["instructions"] = instructions_manager.get_instructions(self.name)
        data["api_applications_list"] = [
            app.name for app in input_variables.api_intent_relevant_apps or [] if app.type == 'api'
        ]
```

**Flow:** controller receives control after CONCLUDE_TASK (API mode) or ConcludeTaskAgent (browser mode); renders the five derived views into user.jinja2 → decides next subtask / completion. Template rendering has DIRECT tests: `tests/unit/test_plan_controller_prompt.py` pins `**Subtask N**:` headers, `- step` bullets, `**Final Answer**: <text>` vs literal `'no answer is returned'` for None final_answer, and the empty-history `**Previous Subtasks**:` block.
**Invariant:** Every slot is DERIVED at call time — none are read raw off state (history dumped to plain dicts, variables bounded to 15 entries, api-only app filter). The image slot is attached only when the ActivityTracker holds screenshots (`tracker.images[-1]`). A porter who passes raw objects instead of these projections changes what the LLM can see (unbounded variable values leak).
**Probe:** `tests/unit/test_plan_controller_prompt.py::TestPlanControllerPrompt::test_stm_history_with_final_answer` (:33) + `::test_stm_history_without_final_answer` (:57) + `::test_stm_history_empty` (:79).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "PlanControllerAgent variables_history stm_all_history format_as_list", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derived-view prompt assembly with explicit bounds (last_n summaries, dumped history) and template-level rendering contracts under test. Adapt slot set to your controller's decisions. Omit the img plumbing unless your tracker captures screenshots.
