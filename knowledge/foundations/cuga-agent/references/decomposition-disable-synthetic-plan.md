<!-- capsule-v2 -->
# TaskDecompositionNode disable path — how does a feature flag fabricate a valid plan without calling the LLM?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When task decomposition is off, what synthetic plan keeps downstream consumers working unchanged?

## Flag-shaped synthetic single-task plan
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/task_decomposition.py:TaskDecompositionNode.node_handler` (:31-70); schema `task_decomposition_agent/prompts/load_prompt.py:TaskDecompositionPlan.format_as_list` (:17-20).
**Signature:** `node_handler(state: AgentState, agent: TaskDecompositionAgent, name: str) -> AgentState` (plain state return, no Command — routing continues via static edges).
**Data Shape:** `TaskDecompositionPlan{thoughts: str, task_decomposition: List[DecomposedTask{task, app, type: Literal['api','web']}]}`; progress mirror `state.sub_tasks_progress: List["not-started"]`.

### Decisive source
```python
        if not settings.features.task_decomposition:
            logger.debug("Task decomposition is disabled")
            task_decomposition_plan = TaskDecompositionPlan(
                thoughts="",
                task_decomposition=[
                    DecomposedTask(
                        task=state.input,
                        app=state.api_intent_relevant_apps[0].name,
                        type=state.api_intent_relevant_apps[0].type,
                    )
                ],
            )
            state.task_decomposition = task_decomposition_plan
            state.sub_tasks_progress = ["not-started"] * len(state.task_decomposition.task_decomposition)
            state.messages.append(AIMessage(content=task_decomposition_plan.model_dump_json()))
```

**Flow:** flag off → whole user input becomes ONE DecomposedTask bound to the FIRST matched app (requires `api_intent_relevant_apps` non-empty — upstream trusts analyzer ordering) → still appended to `messages` as an AIMessage so transcript consumers can't tell the difference → tracker step collected. Flag on → agent runs, multi-site inputs (>1 sites) route to `chain_multi` whose `TaskDecompositionMultiOutput` hard-Literals six WebArena app names; benchmark mode `"appworld"` REWRITES every `type == "web"` subtask to `"api"` post-hoc.
**Invariant:** Downstream (plan controller renders `format_as_list()` — truncated to 30 chars per app name) reads `state.task_decomposition` identically either way; the synthetic path MUST also populate `sub_tasks_progress` or progress-index updates crash later. The AppWorld type-rewrite happens AFTER parse, never inside the prompt.
**Probe:** Recorded upstream gap. Deterministic: `grep -n 'sub_tasks_progress' src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/task_decomposition.py` shows BOTH branches setting it (:53, :66).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "TaskDecompositionNode DecomposedTask format_as_list sub_tasks_progress", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt feature-flag fallbacks that synthesize the exact success-path data shape (plus mirrors like progress arrays) instead of branching downstream. Adapt the multi-output schema to your app registry — upstream's six-name Literal is WebArena-specific and should NOT be generalized blindly. Omit benchmark type-rewrites unless porting AppWorld.
