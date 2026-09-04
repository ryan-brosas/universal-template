<!-- capsule-v2 -->
# SendMessage extra-params discovery — how do subclasses add typed tool parameters without overriding __init__?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** What is the three-pattern discovery ladder for extra parameters, and which annotations must be excluded so base-class internals never leak into the tool schema?

## Nested model → class attr → inline Field declarations
**Path/Symbol:** `src/agency_swarm/tools/send_message.py` `_discover_inline_fields` (:221-266) + schema merge in `__init__` (:121-164) + validation at invoke (:344-355).
**Signature:** `_discover_inline_fields(cls) -> type[BaseModel] | None`; merge writes into `params_json_schema["properties"/"required"/"$defs"]`; runtime check `model_cls(**model_input)` for validation only.
**Data Shape:** three patterns, priority-ordered: (1) nested `class ExtraParams(BaseModel)` on the subclass; (2) class attribute `extra_params_model = MyModel`; (3) inline class-level annotated fields with pydantic `Field()` defaults built via `create_model(f"{cls.__name__}Params", ...)`.

### Decisive source
```python
# Inline discovery: only FieldInfo-or-Ellipsis defaults count as params
base_annotations = set()
for base_cls in SendMessage.__mro__:
    base_annotations.update(getattr(base_cls, "__annotations__", {}).keys())
reserved = {"tool_name"}
for mro_cls in reversed(cls.__mro__):                 # base-to-derived so overrides win
    if mro_cls is SendMessage or not issubclass(mro_cls, SendMessage): continue
    for field_name, annotation in annotations.items():
        if field_name in base_annotations or field_name in reserved or field_name.startswith("_"):
            continue
        if field_name not in mro_cls.__dict__: continue
        default = mro_cls.__dict__[field_name]
        if isinstance(default, FieldInfo) or default is ...:
            extra_field_defs[field_name] = (annotation, default)
...
# Invoke-time validation: filter kwargs to KNOWN fields, validate, discard instance
model_fields = set(model_cls.model_fields.keys())
model_input = {k: v for k, v in kwargs.items() if k in model_fields}
model_cls(**model_input)
```

**Flow:** init tries explicit candidates (`ExtraParams` or `extra_params_model`) then falls back to inline discovery; merged properties/required/$defs are unioned into the base three-field schema preserving order; failures log a warning and ship the BASE schema (degradation, not crash); custom tool NAME comes from a `tool_name` class attribute honored only while caller left name at default.
**Invariant:** (1) Base-class annotations (sender_agent/recipients/_runtime_state/...) are collected across the whole MRO as RESERVED — without that set the tool's own fields would appear as LLM parameters; (2) plain annotated defaults (e.g. `priority: str = "low"`) are deliberately NOT picked up — only `Field(...)` or `...` sentinels mark intent, keeping arbitrary class attrs out of the schema; (3) validation filters to known fields BEFORE constructing, so extra provider junk in kwargs can't fail validation; (4) schema-merge failure degrades silently — a broken subclass must not kill agency construction.
**Probe:** `tests/test_agent_modules/send_message/test_extra_params.py::test_send_message_extra_params_schema_validation_and_success` (:72), `test_inline_fields_merged_into_schema` (:132), `test_bare_annotations_are_not_treated_as_inline_fields` (:191), `test_inline_fields_not_picked_up_when_extra_params_exists` (:174), `test_tool_name_class_attribute` (:152).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "extra params discover inline fields SendMessage", limit: 10 });
```

## Verdict
Adopt the annotation-driven discovery ladder with MRO-wide reserved names; adapt to your tool base's own reserved set; omit the legacy nested-class patterns if you only need inline fields. Five direct tests pin every branch at HEAD.
