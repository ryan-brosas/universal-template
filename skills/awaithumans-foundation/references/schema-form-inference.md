<!-- capsule-v2 -->
# Form Inference from Pydantic Schemas — how does a typed response schema become a human-reviewable form?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you render review UIs from Pydantic models without making developers author form definitions twice?

## Annotated-wins extraction + type-based inference fallback
**Path/Symbol:** `packages/python/awaithumans/forms/extract.py:extract_form` (:24–48) + `forms/infer.py:infer_field_from_type/_unwrap_optional` (:41–118); capability gate `forms/capabilities.py:CAPABILITIES/form_renders_in/unsupported_fields`.
**Signature:** `extract_form(model_cls: type[BaseModel]) -> FormDefinition`; `infer_field_from_type(name, annotation, is_required) -> FormFieldBase`.
**Data Shape:** bool→Switch; str→ShortText; int/float→ShortText(subtype=number); date/datetime/time→pickers; Literal[a,b]→SingleSelect(options); Enum→SingleSelect; list[Enum]→MultiSelect; anything else→LongText. `name`/`required` are ALWAYS overwritten from the model regardless of developer DSL args.

### Decisive source
```python
metadata = list(field_info.metadata or [])
explicit = next((m for m in metadata if isinstance(m, FormFieldBase)), None)
if explicit is not None:
    field = explicit.model_copy(update={
        "name": attr_name, "required": is_required,
        "label": explicit.label or _humanize(attr_name)})
else:
    field = infer_field_from_type(attr_name, field_info.annotation, is_required)
```
Optional-unwrapping handles BOTH union spellings:
```python
origin = get_origin(annotation)
if origin is Union:                       # Optional[X]
    non_none = [a for a in get_args(annotation) if a is not type(None)]
    if len(non_none) == 1: return non_none[0]
union_type = getattr(types, "UnionType", None)   # PEP 604  X | None
if union_type is not None and isinstance(annotation, union_type): ...
```
Channel gate (single source of truth consulted by every renderer):
> If ANY field forces link-out in a channel, THE WHOLE FORM falls back there — typed-response contract preserved whichever way the human answered.

**Flow:** both SDKs synthesize the FormDefinition client-side BEFORE create (`client.py:162`, TS `extractForm(responseSchema)` returning null for unsynthesizable shapes ⇒ server falls back to raw JSON-schema rendering) → server uses it to pick channel rendering — notably email emits Approve/Reject magic-link BUTTONS iff the form is a single Switch, else a dashboard link-out.
**Invariant:** inference is a FALLBACK, never an override; unknown types degrade to LongText rather than erroring; every primitive kind MUST have a CAPABILITIES entry for all four channels or `form_renders_in` crashes (guarded exhaustively by tests).
**Probe:** `tests/forms/test_infer.py` (:35–133 per-type mapping + optional-not-required + long-text fallback), `tests/forms/test_capabilities.py` (ALL_KINDS completeness guard incl. recursive SectionCollapse/Subform walk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "extract_form infer field pydantic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt annotated-metadata-wins + type-inference-fallback, name/required central overwrite, dual-union unwrapping, whole-form channel degradation, and client-side synthesis with server fallback. Adapt primitive vocabulary to your channels. Omit the specific Block Kit renderers (channel-specific surface).
