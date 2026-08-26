<!-- capsule-v2 -->
# Completion kwargs precedence ladder — who wins when model defaults, call kwargs, and named parameters collide?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** In `Model._prepare_completion_kwargs`, what is the exact override order, and how does a user remove a parameter entirely instead of setting it?

## Four-layer merge with REMOVE sentinel
**Path/Symbol:** `src/smolagents/models.py:Model._prepare_completion_kwargs` (:502-551), `REMOVE_PARAMETER`/`_ParameterRemove` (:441-449), `Model.to_dict` secret scrubbing (:620-625).
**Signature:** `_prepare_completion_kwargs(messages, stop_sequences=None, response_format=None, tools_to_call_from=None, custom_role_conversions=None, convert_images_to_image_urls=False, tool_choice="required", **kwargs) -> dict`.
**Data Shape:** Priority (documented in-source, lowest→highest): messages first; then specific params (stop/response_format/tools+tool_choice); then explicit per-call kwargs; finally `self.kwargs` constructor defaults — each later layer overwrites earlier keys wholesale.

### Decisive source
```python
# :543-551 — the last two layers, incl. removal:
completion_kwargs.update(kwargs)                    # call-site overrides
for kwarg_name, kwarg_value in self.kwargs.items():
    if kwarg_value is REMOVE_PARAMETER:
        completion_kwargs.pop(kwarg_name, None)     # delete instead of set
    else:
        completion_kwargs[kwarg_name] = kwarg_value # model defaults win last
```

**Flow:** Message cleaning runs first (`get_clean_message_list` with role conversions + image encoding + consecutive-role merging); `stop` is added ONLY if `supports_stop_parameter(model_id)`; tools become OpenAI-style JSON schemas with `tool_choice="required"` default. Because constructor defaults are applied LAST, `Model(..., temperature=0)` beats an ad-hoc call kwarg — and passing `temperature=REMOVE_PARAMETER` deletes the key so provider-side defaults apply. Bedrock's override shows the ladder's extensibility: it strips `toolConfig` and every content-block `"type"` key post-hoc because its API forbids them.
**Invariant:** The sentinel must be checked BEFORE plain assignment in the same loop, or a REMOVE arriving after a call-kwarg would re-add nothing but also fail to pop. Porters who flatten this into `{**self.kwargs, **kwargs}` invert the intended precedence AND lose removal.
**Probe:** `tests/test_models.py` precedence fixtures around `_prepare_completion_kwargs` usage + `test_supports_stop_parameter` matrix (:911-913). Live: construct `OpenAIModel(..., temperature=REMOVE_PARAMETER)` and inspect `_prepare_completion_kwargs(...)["keys"]` for absence of `temperature`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_prepare_completion_kwargs REMOVE_PARAMETER completion_kwargs", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the documented four-layer order and the REMOVE sentinel. Adapt layer names to your config surface. Omit to_dict's secret-scrub warning at your peril (`token`/`api_key` deliberately never serialized).
