<!-- capsule-v2 -->
# `as_ser_schema` + core-schema type guards — which schema kinds are "fields" vs "core", and how does any core schema become a SerSchema?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What are the canonical predicate sets for walking a CoreSchema tree, and what is the fallback serialization shape for function schemas?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_core_utils.py:_CORE_SCHEMA_FIELD_TYPES` (:33), `_FUNCTION_WITH_INNER_SCHEMA_TYPES` (:34), `as_ser_schema` (:56-76).
**Signature:** `is_core_schema(s) / is_core_schema_field(s) / is_function_with_inner_schema(s) -> TypeGuard[...]`; `def as_ser_schema(schema: CoreSchema) -> core_schema.SerSchema`.
**Data Shape:** Sets: fields = `{typed-dict-field, dataclass-field, model-field, computed-field}`; function-with-inner = `{function-before, function-after, function-wrap}`; list-like-with-items = `{list, set, frozenset}`.

### Decisive source
```python
def as_ser_schema(schema: CoreSchema) -> core_schema.SerSchema:
    """Any core schema can be used as a serialization schema, except 'function-plain' and 'function-wrap'
    schemas ... For these, mimic what pydantic-core would do if they were used as the *main* schema:
    - if the function schema has a 'serialization' schema, use it.
    - otherwise, a 'function-plain' schema is serialized as 'any', and a 'function-wrap' schema
      is serialized using its inner schema."""
    if schema['type'] == 'function-plain' or schema['type'] == 'function-wrap':
        if (ser_schema := schema.get('serialization')) is not None:
            return ser_schema
        if schema['type'] == 'function-plain':
            return core_schema.any_schema()
        return as_ser_schema(schema['schema'])
    return schema
```

**Flow:** predicates partition the schema universe so generic walkers (discriminator inference, gather, JSON-schema) never special-case per call site; `as_ser_schema` recurses into the wrap-variant's inner schema until it finds a serializable leaf.
**Invariant:** `'function-after'` HAS an inner schema but is NOT in the ser-conflict set (its own name is free as a SerSchema type); the plain/wrap names collide with serializer FUNCTION schema types — that collision is the entire reason this helper exists. Treat these string sets as the compatibility contract with pydantic-core's schema vocabulary.
**Probe:** `grep -n '_FUNCTION_WITH_INNER_SCHEMA_TYPES = ' pydantic/_internal/_core_utils.py` (:34 pins the exact member set).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "as_ser_schema function plain wrap inner", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the partition sets + ser-fallback recursion when building your own schema walkers; adapt naming to your schema vocabulary; omit rich pretty-printing helpers.
