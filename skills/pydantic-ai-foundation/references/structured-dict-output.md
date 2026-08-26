<!-- capsule-v2 -->
# StructuredDict — attaching a raw JSON schema to a runtime type without a model class

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How can users declare structured output as a plain dict constrained by a hand-written JSON schema, no Pydantic model required?

## StructuredDict factory
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/output.py:StructuredDict` (:352-416), `_utils.check_object_json_schema`, `InlineDefsJsonSchemaTransformer` (`_json_schema.py`).
**Signature:** `StructuredDict(json_schema: JsonSchemaValue, name: str | None = None, description: str | None = None) -> type[JsonSchemaValue]`.
**Data Shape:** Returns a NEW class subclassing `pydantic.JsonSchemaValue` (i.e. `dict[str, Any]`) with `__is_model_like__ = True`, a dict core schema, and a `__get_pydantic_json_schema__` that RETURNS THE USER SCHEMA verbatim.

### Decisive source
```python
# output.py:383-390 — $defs must be inlined or TypeAdapter explodes; recursion is rejected loudly
# Pydantic `TypeAdapter` fails when `object.__get_pydantic_json_schema__` has `$defs`, so we inline them
# See https://github.com/pydantic/pydantic/issues/12145
if '$defs' in json_schema:
    json_schema = InlineDefsJsonSchemaTransformer(json_schema).walk()
    if '$defs' in json_schema:
        raise exceptions.UserError(
            '`StructuredDict` does not currently support recursive `$ref`s and `$defs`. ...')

class _StructuredDict(JsonSchemaValue):
    __is_model_like__ = True

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.dict_schema(keys_schema=core_schema.str_schema(),
                                       values_schema=core_schema.any_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return json_schema  # the user's schema, captured in the closure
```

**Flow:** Validate the schema is an object schema → inline top-level `$defs` (Pydantic bug #12145 workaround); if refs remain after inlining it's recursive → UserError → stamp title/description from args (falling back to whatever the user's schema already carried) → return the closure-captured class. Downstream, because the class answers BOTH schema hooks, every processor path (`ObjectOutputProcessor`, union members, tool lowering) treats it exactly like a BaseModel while validation accepts any dict matching the shape.
**Invariant:** The two-hook split IS the trick: validation stays permissive (`dict[str, Any]`), while the MODEL-FACING JSON schema is authoritative — porters who instead build a strict validator from the JSON schema break round-tripping of unknown-but-permitted keys and provider-specific extras.
**Probe:** `tests/test_agent_output_schemas.py` (StructuredDict cases incl. `$defs` inlining; search `StructuredDict(` — exercised via `Agent(output_type=StructuredDict(schema))` end-to-end runs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "StructuredDict JsonSchemaValue check_object_json_schema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-core-schema/json-schema class factory for schema-only outputs; adapt to your validation stack; omit if your host requires typed models everywhere. Caveat: probe coverage is integration-level (end-to-end agent tests), not a unit test on the factory.
