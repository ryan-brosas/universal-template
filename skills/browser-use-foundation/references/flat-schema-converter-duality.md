<!-- capsule-v2 -->
# Flat schema converter duality — permissive vendor converters vs fail-closed local grammar

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how strictly should you validate action-parameter schemas, given WHO authored the schema?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/skills/utils.py`: `convert_parameters_to_pydantic` (:10-63), `convert_json_schema_to_pydantic` (:66-140) — contrasted with `browser_use/tools/extraction/schema_utils.py` reject-list grammar (see extraction-dual-path).
**Signature:** `convert_parameters_to_pydantic(parameters: list[ParameterSchema], model_name='SkillParameters') -> type[BaseModel]`; `convert_json_schema_to_pydantic(schema: dict, model_name='SkillOutput') -> type[BaseModel]`.
**Data Shape:** unknown types degrade to `str` (never raise); optional = `X | None` + `Field(default=None)`; required fields carry NO default (pydantic `PydanticUndefined` — probed); JSON-schema arrays map `items.type` ONE level deep else `list[Any]`; empty input → bare `create_model(model_name)`.

### Decisive source
```python
python_type: Any = str  # default — UNKNOWN TYPES DEGRADE, never raise   # :29
elif param_type == 'cookie':
    python_type = str  # Treat cookies as strings                         # :43-44
is_required = param.required if param.required is not None else True      # :47

# utils.py :76-78 — the docstring itself declares the trust boundary
# Note:
#     This is a simplified converter that handles basic types.
#     For complex nested schemas, consider using datamodel-code-generator.
```

**Flow:** vendor skill arrives with a flat ParameterSchema list or shallow JSON Schema -> converter builds a pydantic model via `create_model` -> LLM fills it -> execution validates. The SAME repo's LOCAL extraction path (`tools/extraction/schema_utils.py`) instead REJECTS `$ref/allOf/anyOf/oneOf/not/$defs/definitions/if/then/else/dependentSchemas/dependentRequired` with ValueError and widens enums to str ("Literal would be stricter but LLMs are flaky").
**Invariant:** two converters, two philosophies, chosen by TRUST BOUNDARY: locally-authored schemas get the strict grammar (fail closed at admission, before any side effect); vendor-supplied skill schemas get the permissive one (degrade to `str`, never break on drift we don't control). Optional fields serialize as absent→None; required fields must be explicitly provided. DRIFT note: at this pin `'cookie'` never matches because `ParameterSchema.type` is an enum, so the cookie branch maps through the UNKNOWN→str fallback anyway — same outcome, right result by accident (see skill-cookie-param-injection).
**Probe:** `.venv/bin/python -c` from repo root: optional param → annotation `str | None`, default None, not required; required cookie param → `<class 'str'>`, default `PydanticUndefined`, required; json-schema `{xs:{array,integer},dt:datetime}` → `list[int] | None` and `str | None` (unknown type degrades); `{}` → 0-field model (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "convert parameters json schema pydantic create_model", limit: 10 });
```
Executed during discovery: rank-3 `convert_parameters_to_pydantic` :10-63.

## Verdict
Adopt the dual-grammar principle and the exact optionality ladder (`X | None` + `default=None` vs no-default-required). Adapt type tables to your host types. Omit nothing structural: if you collapse to one converter you will either crash on vendor drift or under-validate your own agent's actions. Cross-ref extraction-dual-path for where the strict grammar lives and how overflow/admission share its fail-closed posture.
