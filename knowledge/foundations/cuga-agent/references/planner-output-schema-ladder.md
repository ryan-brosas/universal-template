<!-- capsule-v2 -->
# Planner schema ladder — how do four output schemas cover thoughts×HITL without breaking one parser?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How can one router serve small models with no `thoughts` field and deployments with HITL disabled while downstream code consumes a single schema?

## Model-capability-probed schema selection with lite→full repack
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/api_planner_agent/api_planner_agent.py:_get_model_identifier` (:40-69), `APIPlannerAgent.__init__` (:72-85), `run` (:91-125).
**Signature:** `_get_model_identifier(llm: BaseChatModel) -> Optional[str]`; schema pick: `APIPlannerOutput | APIPlannerOutputLite | APIPlannerOutputNoHITL | APIPlannerOutputLiteNoHITL`.
**Data Shape:** identifier probed per provider class — ChatWatsonx `.model_id`, ChatOpenAI `.model_name`, ChatGroq `.model`, else attribute walk `model_id → model_name → model`.

### Decisive source
```python
        model_id = _get_model_identifier(llm)
        self.thoughts_enabled = not (model_id and "oss" in model_id) and settings.features.thoughts

        if settings.advanced_features.api_planner_hitl:
            schema = APIPlannerOutputLite if not self.thoughts_enabled else APIPlannerOutput
        else:
            schema = APIPlannerOutputLiteNoHITL if not self.thoughts_enabled else APIPlannerOutputNoHITL
```
and the repack that restores the FULL shape downstream:
```python
            full_res = APIPlannerOutput(
                thoughts=[],
                action=lite_res.action,
                action_input_shortlisting_agent=lite_res.action_input_shortlisting_agent,
                ...
            )
```

**Flow:** create() picks hitl/non-hitl jinja prompt pair to match the schema; `run()` invokes the chosen chain; if thoughts were disabled the Lite result is REPACKED into `APIPlannerOutput` with `thoughts=[]` (and `action_input_consult_with_human=None` when HITL off) so `ApiPlanner.node_handler` always sees one schema; the reverse case (thoughts enabled but HITL off) nulls just the consult field.
**Invariant:** Downstream consumers are written against `APIPlannerOutput` ONLY — the lite variants must never leak past `run()`. The `"oss" in model_id` probe means renaming a proxy model can silently flip schema strictness; keep the substring contract documented when porting.
**Probe:** No direct unit test at HEAD. Deterministic: `sed -n '78,85p' src/cuga/backend/cuga_graph/nodes/api/api_planner_agent/api_planner_agent.py` matches the selection block; sibling suite `tests/unit/test_base_agent_claude_json_schema.py` covers the underlying chain dialects.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_get_model_identifier APIPlannerOutputLite thoughts_enabled", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-probed schema narrowing with a single canonical shape leaving the agent boundary; adopt the provider-attribute identifier walk as the safe way to read a BaseChatModel's model name. Adapt the feature flags and model-id substrings. Omit the Watsonx/Groq branches you don't carry.
