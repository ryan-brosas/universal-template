<!-- capsule-v2 -->
# llm-max-token-recalc — How do you stop prompt+completion from silently exceeding a model's context window?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the clamp rule when configured max_tokens plus the actual prompt overflows the context?

## Overflow clamp with 16-token floor and use_template alias resolution
**Path/Symbol:** `api/core/app/apps/base_app_runner.py:AppRunner.recalc_llm_max_tokens` (:56-88).
**Signature:** `recalc_llm_max_tokens(model_config: ModelConfigWithCredentialsEntity, prompt_messages: list[PromptMessage])`.
**Data Shape:** Reads `ModelPropertyKey.CONTEXT_SIZE` from the model schema; scans `parameter_rules` for `max_tokens` by name OR by `use_template == "max_tokens"` alias; mutates `model_config.parameters[name]` in place; returns -1 sentinel when no context size is declared.

### Decisive source
```python
def recalc_llm_max_tokens(self, model_config, prompt_messages):
    # recalc max_tokens if sum(prompt_token + max_tokens) over model token limit
    model_instance = ModelInstance(provider_model_bundle=model_config.provider_model_bundle, model=model_config.model)
    model_context_tokens = model_config.model_schema.model_properties.get(ModelPropertyKey.CONTEXT_SIZE)

    max_tokens = 0
    for parameter_rule in model_config.model_schema.parameter_rules:
        if parameter_rule.name == "max_tokens" or (
            parameter_rule.use_template and parameter_rule.use_template == "max_tokens"
        ):
            max_tokens = (model_config.parameters.get(parameter_rule.name)
                          or model_config.parameters.get(parameter_rule.use_template or "")) or 0

    if model_context_tokens is None:
        return -1                      # unknown window: never guess

    prompt_tokens = model_instance.get_llm_num_tokens(prompt_messages)
    if prompt_tokens + max_tokens > model_context_tokens:
        max_tokens = max(model_context_tokens - prompt_tokens, 16)   # floor of 16
        for parameter_rule in model_config.model_schema.parameter_rules:
            if parameter_rule.name == "max_tokens" or (
                parameter_rule.use_template and parameter_rule.use_template == "max_tokens"
            ):
                model_config.parameters[parameter_rule.name] = max_tokens
```

**Flow:** resolve current max_tokens (name first, then template alias; missing ⇒ 0) → tokenize the ACTUAL prompt → only on overflow rewrite the parameter to `context − prompt` floored at 16 → write under the CANONICAL name even when discovered via alias.
**Invariant:** No-context-size models return -1 untouched (never assume); the 16 floor prevents degenerate zero/negative completions when the prompt alone nearly fills the window; the rewrite targets the canonical key so downstream consumers read one place.
**Probe:** `grep -c 'max(model_context_tokens - prompt_tokens, 16)' core/app/apps/base_app_runner.py` → 1; direct tests `tests/unit_tests/core/app/apps/test_base_app_runner.py::test_recalc_llm_max_tokens_updates_parameters`, `::test_recalc_llm_max_tokens_returns_minus_one_when_no_context`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppRunner recalc llm max tokens context size", limit: 10 });
```

## Verdict
Adopt overflow-only clamping with the 16 floor and alias-aware discovery. Adapt the tokenizer seam and property keys. Omit the -1 convention if your config validates context size upfront.
