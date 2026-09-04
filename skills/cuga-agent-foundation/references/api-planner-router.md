<!-- capsule-v2 -->
# APIPlanner router node — how does one LangGraph node dispatch four actions plus a zero-LLM fast path?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where exactly do the early-exit fast path, the HITL consult round-trip, and each planner action write state, and which edges exist even though the LLM never names them?

## Command-router node with early CugaLite exit
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/api_planner.py:ApiPlanner.node_handler` (:146-317), `should_use_fast_mode_early` (:107-125), `count_tools_for_app` (:127-144).
**Signature:** `node_handler(state: AgentState, agent: APIPlannerAgent, strategic_agent, name: str) -> Command[Literal['APICodePlannerAgent','ShortlisterAgent','PlanControllerAgent','SuggestHumanActions','CugaLite']]`.
**Data Shape:** returns `Command(update=state.model_dump(), goto=<node>)` everywhere — full-state replacement, so EVERY mutation before the return must land on `state`, never on locals.

### Decisive source
```python
        if ApiPlanner.should_use_fast_mode_early(state):
            if state.sub_task_app:
                tool_count = await ApiPlanner.count_tools_for_app(current_app_name)
                threshold = settings.advanced_features.lite_mode_tool_threshold
                if tool_count < threshold:
                    return Command(update=state.model_dump(), goto="CugaLite")
```
and the dispatch tail — note the unconditional fallthrough:
```python
        if settings.advanced_features.api_planner_hitl and res.action == ActionName.CONSULT_WITH_HUMAN:
            ...
            return Command(update=state.model_dump(), goto="SuggestHumanActions")

        return Command(update=state.model_dump(), goto="APICodePlannerAgent")
```

**Flow:** (0) fast-mode gate BEFORE any LLM call: `lite_mode` resolves `state.lite_mode if not None else settings…`, requires mode ∈ {'api','hybrid'}, then counts registered tools for `sub_task_app` (count errors → 0, never raise) and exits to CugaLite when below threshold; (1) HITL consult-response merge when `sender == WaitForResponse` — human text/selected-values appended to `api_planner_human_consultations` then `sender = name` so the planner LLM sees it; (2) post-coder reflection when `api_last_step == CODER_AGENT` and `features.code_output_reflection`: strategic summary → `state.guidance` (cleared again at :217 right after the next planner run); (3) strict→tolerant parse of planner output; (4) action switch — CODER_AGENT fans `task_description/context_variables_from_history/relevant_apis` into `coder_*` fields and re-filters cached shortlist via `ShortlisterAgent.filter_by_api_names` → APICodePlannerAgent; API_FILTERING_AGENT composes `shortlister_query` as `"**Input task**: {desc}\n\nTask context:{sub_task}"` → ShortlisterAgent; CONCLUDE_TASK appends `SubTaskHistory(final_response)` and sets `sender="APIPlannerAgent"` → PlanControllerAgent; CONSULT_WITH_HUMAN builds a `FollowUpAction` (suggested_options ⇒ ActionType.SELECT with SelectOption list, else NATURAL_LANGUAGE) → SuggestHumanActions.
**Invariant:** The fallthrough edge APICodePlannerAgent exists for ANY unmodeled action value — the graph validates because every declared Literal target has at least one static edge. `should_use_fast_mode_early` must stay before the first `agent.run` or the "skip all LLM calls" contract breaks. `count_tools_for_app` swallows ALL exceptions to 0 — a registry outage therefore ROUTES TO LITE rather than failing the run.
**Probe:** `tests/unit/test_shortlister_config_surfaces.py` pins adjacent config surfaces; deterministic: `sed -n '158,174p' src/cuga/backend/cuga_graph/nodes/api/api_planner.py` shows the threshold block above the HITL merge.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ApiPlanner should_use_fast_mode_early count_tools_for_app node_handler", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full-state `Command(update=model_dump(), goto=…)` idiom, the zero-LLM tool-count fast path, and the count-errors-route-anyway degradation. Adapt action enum names and target nodes to your own topology. Omit AppWorld/WebArena-specific benchmark branches unless porting that harness.
