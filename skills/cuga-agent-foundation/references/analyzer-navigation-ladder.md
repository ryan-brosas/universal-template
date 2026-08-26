<!-- capsule-v2 -->
# TaskAnalyzer read-only navigation ladder — which analyzer calls run for admin apps, and why is paraphrase fed forward?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the analyzer combine classification, intent paraphrase, and navigation-path planning with per-call temperature overrides?

## Conditional sub-task ladder over shared chain factories
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/task_analyzer_agent/task_analyzer_agent.py:TaskAnalyzerAgent.run` (:41-93); factories `tasks/navigation_paths_task.py` (:24-33), `tasks/paraphrase.py` (:18-27).
**Signature:** `run(input_variables: AgentState) -> AIMessage` (content = `AnalyzeTaskOutput` JSON); each factory: `navigation_paths_task(model_config) -> Runnable` returning `BaseAgent.get_chain(prompt, llm, Approaches)`.
**Data Shape:** `Approach{approach: str, extensive_pagination: bool, estimated_steps: int}`; `Approaches{thoughts: List[str], approaches: List[Approach]}`; `Paraphrase{thoughts, rephrased_intent}`.

### Decisive source
```python
            if settings.advanced_features.use_paraphrase:
                task_analyzer_output.paraphrased_intent = (
                    await self.paraphrase_task.with_config(configurable={"llm_temperature": 0.1}).ainvoke(inp)
                ).rephrased_intent
                ...
                inp['input'] = task_analyzer_output.paraphrased_intent   # feeds FORWARD
            ...
            approaches: Approaches = await self.navigation_paths_task.with_config(
                configurable={"llm_temperature": 0.3}
            ).ainvoke(inp)
            task_analyzer_output.navigation_paths.approaches = sorted(
                ..., key=lambda obj: obj.extensive_pagination
            )
```

**Flow:** webarena-only classify_task fills `Attributes`; the navigation ladder fires ONLY when attrs say not-update AND current_app ∈ {'gitlab','shopping_admin'} — i.e. read-only intents on admin-heavy apps. Paraphrase (temp 0.1) output REPLACES `inp['input']` before navigation paths are planned (temp 0.3); approaches sorted so non-extensive pagination first; everything lands in one `AnalyzeTaskOutput` JSON message.
**Invariant:** Per-call temperature rides `Runnable.with_config(configurable={"llm_temperature": …})`, NOT a new LLMManager model — the override must survive whatever chain wrapper `get_chain` built. The feed-forward rewrite means navigation sees the REPHRASED intent; reordering breaks that coupling. Outside the gate, attrs stay the all-False default constructed at :54-60.
**Probe:** Direct tests pin app matching (`tests/unit/test_task_analyzer_app_matching.py`) and template rendering (`tests/unit/test_plan_controller_prompt.py`); this ladder itself is source-pinned. Deterministic: `grep -c "with_config" src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/task_analyzer_agent/task_analyzer_agent.py` = 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "TaskAnalyzerAgent navigation_paths_task paraphrase_task with_config llm_temperature", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-call temperature overrides via with_config on composed chains and the read-only-intent gating idea. Adapt app names, cutoffs, and prompt templates. Omit webarena benchmark branches; treat the six-app maps as demo data.
