<!-- capsule-v2 -->
# Function-call schema projection — how do parameter metadata become a provider tool schema, and where is it installed?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When the kernel advertises a function to a model, what exactly goes into the JSON schema for each parameter, when is that schema computed, and how does it get into the outgoing request?

## Schema frozen at metadata construction time
**Path/Symbol:** `python/semantic_kernel/functions/kernel_parameter_metadata.py:KernelParameterMetadata.form_schema` (26–35) + `infer_schema` (38–63); builder `python/semantic_kernel/schema/kernel_json_schema_builder.py:KernelJsonSchemaBuilder.build` (38–65), `build_model_schema` (67–111), `build_from_type_name` (117–152), `handle_complex_type` (154–218), `build_enum_schema` (220–237).
**Signature:** `@model_validator(mode="before") @classmethod def form_schema(cls, data: Any) -> Any`.
**Data Shape:** `schema_data: dict[str, Any] | None` is filled ONCE at metadata construction (only when not already supplied). A concrete `type_object` routes to `KernelJsonSchemaBuilder.build`: pydantic models → object schema derived via `get_type_hints` with per-field descriptions and required-ness from Optionality; Enums → `{"type": <value-type>, "enum": [...]}`; unions/generics → `anyOf` composition. A string `type_` (no type object) routes through `TYPE_MAPPING` (`int→integer`, `str→string`, `bool→boolean`, `float→number`, `list/set/tuple→array`, `dict/object→object`) with unknown names degrading to `"object"`. Non-empty defaults are folded INTO the description text as `(default value: X)` rather than emitted as a JSON-Schema `default`.

### Decisive source
```python
if isinstance(data, dict) and data.get("schema_data") is None:
    type_object = data.get("type_object", None)
    type_ = data.get("type_", None)
    default_value = data.get("default_value", None)
    description = data.get("description", None)
    inferred_schema = cls.infer_schema(type_object, type_, default_value, description)
    data["schema_data"] = inferred_schema
return data
# infer_schema: concrete type wins over type name; string defaults are TEXT, not schema defaults
if type_object is not None:
    schema = KernelJsonSchemaBuilder.build(type_object, description, structured_output)
elif parameter_type is not None:
    ...
    schema = KernelJsonSchemaBuilder.build_from_type_name(parameter_type, description)
```

**Flow:** metadata construction infers and stores the schema; every later consumer (tool-view projection, prompt-function parameter lists) just reads `schema_data`. Prompt functions are the notable case: their parameters carry only a string `type_` (the InputVariable's `json_schema`), so they always take the type-name mapping path.
**Invariant:** the projection step is a pure read — by the time metadata exists, each parameter's schema is frozen; changing an annotation requires rebuilding the metadata. Defaults travel as description prose, so a model sees them but the schema never constrains them.
**Probe:** `python/tests/unit/services/test_service_utils.py::test_complex_schema` (236–283, nested pydantic object with per-field descriptions and required list); `::test_union_plugin` (348–381, `str | int` → `anyOf` of two typed branches); `::test_enum_plugin` (384–410, enum values as `enum` list); `::test_datetime_parameter` (413–442, datetime field degrades to `{"type": "object"}`).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Projection + duck-typed install
**Path/Symbol:** `python/semantic_kernel/connectors/ai/function_calling_utils.py:kernel_function_metadata_to_function_call_format` (42–55), `update_settings_from_function_call_configuration` (24–35).
**Signature:** `def kernel_function_metadata_to_function_call_format(metadata: KernelFunctionMetadata) -> dict[str, Any]`.
**Data Shape:** output is the provider tool shape `{"type": "function", "function": {name, description, parameters}}`; a flatter response-API twin exists at 62–75. Install mutates the settings object in place.

### Decisive source
```python
"parameters": {
    "type": "object",
    "properties": {
        param.name: param.schema_data for param in metadata.parameters if param.include_in_function_choices
    },
    "required": [p.name for p in metadata.parameters if p.is_required and p.include_in_function_choices],
},
# install: capability-checked, no-op for settings without both attributes
if (function_choice_configuration.available_functions
        and hasattr(settings, "tool_choice") and hasattr(settings, "tools")):
    settings.tool_choice = type
    settings.tools = [kernel_function_metadata_to_function_call_format(f)
                      for f in function_choice_configuration.available_functions]
```

**Flow:** project each chosen metadata entry (name = fully-qualified `plugin-function`, description or `""`); keep only parameters flagged `include_in_function_choices=True` in BOTH properties and required; then install into settings only when the available set is non-empty AND the settings object actually has `tool_choice` and `tools` attributes.
**Invariant:** `include_in_function_choices=False` removes a parameter from the model's view entirely (it cannot be advertised optional either); providers whose settings class lacks the two attributes are left untouched — the install is duck-typed, not forced.
**Probe:** `python/tests/unit/services/test_service_utils.py::test_bool_schema` (139–161, exact-dict equality including FQN name `"BooleanPlugin-GetBoolean"` and `required: ["value"]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "kernel_function_metadata_to_function_call_format schema_data include_in_function_choices update_settings_from_function_call_configuration", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the two-phase split — compute schemas once at metadata construction, project them read-only at request time — plus the dual-gate parameter visibility rule (`include_in_function_choices` AND `is_required`) and the capability-checked install. Adapt the exact tool-dict shape to your provider wire format and the default-as-description convention to your schema dialect (JSON Schema supports real `default`). Omit nothing from the unknown-type degradation: falling back to `"object"` keeps unrepresentable types callable instead of breaking registration.
