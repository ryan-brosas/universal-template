<!-- capsule-v2 -->
# prepare_request — profile-driven request normalization and output-mode resolution

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter normalizes a model request before it reaches a provider adapter, what is the exact order of merges, mode resolution, field resets, and capability checks that `prepare_request` performs — and how does the model profile drive it?

## Model.prepare_request normalization pipeline
**Path/Symbol:** `pydantic_ai/models/__init__.py:Model.prepare_request` (595-688), `profile` (863-903), `prepare_messages` (690-783).
**Signature:** `prepare_request(model_settings, model_request_parameters) -> tuple[ModelSettings | None, ModelRequestParameters]`.
**Data Shape:** `self.profile` is a `ModelProfile` dict resolved as `DEFAULT_PROFILE` → provider `model_profile(model_name)` → user `profile=` (partial dict or callable) → native-tools intersection.

### Decisive source
```python
model_settings = merge_model_settings(self.settings, model_settings)
params = self.customize_request_parameters(model_request_parameters)
params = prepare_return_schemas(params, supports_tool_return_schema=self.profile.get('supports_tool_return_schema', False))
# resolve 'thinking' from model_settings into params, strip from settings
if model_settings and 'thinking' in model_settings:
    if supports_thinking or thinking_always_enabled:
        if not (thinking_value is False and thinking_always_enabled):
            params = replace(params, thinking=thinking_value)
    model_settings = stripped (without 'thinking')
# dedupe native tools by unique_id
params = params.with_default_output_mode(self.profile.get('default_structured_output_mode', 'tool'))
# reset irrelevant fields per output_mode
if params.output_tools and params.output_mode != 'tool': params = replace(params, output_tools=[])
if params.output_object and params.output_mode not in ('native','prompted'): params = replace(params, output_object=None)
if params.prompted_output_template and params.output_mode not in ('prompted','native'): params = replace(params, prompted_output_template=None)
# set default prompted template
if (params.output_mode == 'prompted' or (params.output_mode == 'native' and profile.get('native_output_requires_schema_in_instructions', False))) \
   and params.prompted_output_template is None:
    params = replace(params, prompted_output_template=profile.get('prompted_output_template', DEFAULT_PROMPTED_OUTPUT_TEMPLATE))
# capability checks
if params.output_mode == 'native' and not profile.get('supports_json_schema_output', False): raise UserError(...)
if params.output_mode == 'tool' and not profile.get('supports_tools', True): raise UserError(...)
if params.allow_image_output and not profile.get('supports_image_output', False): raise UserError(...)
# tool visibility resolution
if params.native_tools or any(t.unless_native or t.with_native or t.defer_loading for t in params.function_tools):
    params = self._resolve_request_tools(params)
else:
    params = replace(params, tool_visibility={t.name: 'visible' for t in params.function_tools})
```

**Flow:** (1) merge model settings; (2) apply `customize_request_parameters`; (3) `prepare_return_schemas`; (4) resolve `thinking` out of settings into params; (5) dedupe native tools; (6) apply `with_default_output_mode(profile['default_structured_output_mode'])`; (7) reset fields irrelevant to the resolved mode; (8) set the default prompted template; (9) capability checks (native/tool/image support); (10) resolve tool visibility (deferred/native swap) or stamp all-visible. `profile` resolution: `DEFAULT_PROFILE` → provider defaults → user override (dict merged or callable) → native-tools intersection with the model class's implemented tools.
**Invariant:** `prepare_request` is idempotent-ish and must be called at the start of every `request`/`request_stream`. `with_default_output_mode` applies the profile's default mode only when the caller hasn't set one. Field resets are mode-conditional (output_tools only in tool mode, output_object only in native/prompted). The `tool_visibility` dict is always stamped (never `None`) after `prepare_request`. Capability support is checked against the profile, raising `UserError` on unsupported modes.
**Probe:** `tests/models/` cover profile-driven mode resolution and prepare_request behavior per provider adapter.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "prepare_request with_default_output_mode _resolve_request_tools profile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the normalization pipeline order and the profile-driven mode/capability resolution; adapt the `ModelProfile` keys to your host's capability model; omit nothing — the mode-conditional field resets and always-stamped tool_visibility are the portable invariants. Coverage clean.
