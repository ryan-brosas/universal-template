<!-- capsule-v2 -->
# Prompt-template contract — how are Jinja templates validated, and what variables does each agent type inject?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What stops a half-specified custom `prompt_templates` dict from silently producing broken system prompts, and exactly which template variables exist per agent class?

## StrictUndefined + shape assertion at init
**Path/Symbol:** `src/smolagents/agents.py:populate_template` (:102-107), `EMPTY_PROMPT_TEMPLATES`/shape assertions (:183-192, :315-326), `PromptTemplates` TypedDict (:166-180); YAML sources `prompts/code_agent.yaml`, `structured_code_agent.yaml`, `toolcalling_agent.yaml`; CodeAgent vars (:1620-1636), ToolCallingAgent vars (:1265-1274), planning vars (:650-709), final-answer vars (:810-845).
**Signature:** `populate_template(template, variables) -> str` — compiled with `undefined=StrictUndefined`; custom templates assert FULL key coverage incl. every sub-dict key.
**Data Shape:** Template keys: system_prompt, planning{initial_plan, update_plan_pre_messages, update_plan_post_messages}, managed_agent{task, report}, final_answer{pre_messages, post_messages}.

### Decisive source
```python
# :102-107 — any missing variable is a loud render error, never an empty string:
compiled_template = Template(template, undefined=StrictUndefined)
try:    return compiled_template.render(**variables)
except Exception as e:
    raise Exception(f"Error during jinja template rendering: {type(e).__name__}: {e}")
# :321-326 — nested-key completeness check against the canonical empty shape:
for key, value in EMPTY_PROMPT_TEMPLATES.items():
    if isinstance(value, dict):
        for subkey in value.keys():
            assert key in prompt_templates.keys() and (subkey in prompt_templates[key].keys()), ...
```

**Flow:** Agent init either loads packaged YAML (CodeAgent picks structured variant when `use_structured_outputs_internally=True`) or validates the user's dict for exact key parity (extra keys tolerated, missing subkeys fatal). System prompt renders at EVERY run() (:477) with agent-type-specific variables: CodeAgent injects authorized_imports (with the `"*"` → "You can import from any package you want." special case), code_block opening/closing tags, custom_instructions; ToolCallingAgent injects tools+managed_agents+custom_instructions. Planning templates additionally get `remaining_steps = max_steps - step`; final-answer templates get task only; managed_agent templates get name/task or name/final_answer.
**Invariant:** StrictUndefined means template drift fails at first render with the offending variable named — porters who switch to default-undefined ship agents whose prompts silently lose tool lists when a rename lands. The system_prompt property is READ-ONLY by design (setter raises) to force edits through prompt_templates.
**Probe:** `tests/test_agents.py::test_instantiation_with_prompt_templates` (:979-989), `test_tool_descriptions_get_baked_in_system_prompt/:test_module_imports_get_baked_in_system_prompt` (:522-536). Live: pass prompt_templates missing planning.update_plan_post_messages → AssertionError naming the subkey.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "populate_template EMPTY_PROMPT_TEMPLATES initialize_system_prompt", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt strict-undefined rendering plus whole-shape validation for any prompt-pack surface. Adapt variable names freely but keep them documented per class. Omit the read-only property guard and users will mutate stale rendered copies instead of templates.
