<!-- capsule-v2 -->
# Model-validator inner/outer split — where do before/after/wrap model validators sit relative to the fields schema and serializers?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When compiling a model's core schema, at which two points are model validators applied, and which modes land at each?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generate_schema.py:_model_schema` (:928-955 call sites) + `apply_model_validators` (:2644-2688).
**Signature:** `apply_model_validators(schema, validators: Iterable[Decorator[ModelValidatorDecoratorInfo]], mode: Literal['inner', 'outer', 'all']) -> CoreSchema`.
**Data Shape:** schema tree mutated in place per validator; each application pops and later restores the `'ref'` key.

### Decisive source
```python
inner_schema = apply_validators(fields_schema, decorators.root_validators.values())
inner_schema = apply_model_validators(inner_schema, model_validators, 'inner')

model_schema = core_schema.model_schema(cls, inner_schema, ..., ref=model_ref)

schema = self._apply_model_serializers(model_schema, decorators.model_serializers.values())
schema = apply_model_validators(schema, model_validators, 'outer')
return self.defs.create_definition_reference_schema(schema)

# apply_model_validators:
ref: str | None = schema.pop('ref', None)
for validator in validators:
    if mode == 'inner' and validator.info.mode != 'before':
        continue
    if mode == 'outer' and validator.info.mode == 'before':
        continue
    info_arg = inspect_validator(validator.func, mode=validator.info.mode, type='model')
    ...with_info/no_info_{wrap,before,after}_validator_function...
if ref:
    schema['ref'] = ref
```

**Flow:** fields schema built → v1 root validators applied → model validators with mode 'inner' (ONLY 'before') wrapped INSIDE the model_fields_schema so they see the raw input dict → model_schema constructed with the ref → model serializers applied → 'outer' application wraps everything EXCEPT 'before' around the finished model schema → definition-reference created. Root models apply 'inner' directly to the root field's `_common_field_schema`; TypedDict/namedtuple paths (:1526) use 'all' on one schema.
**Invariant:** every application strips `'ref'` before wrapping function schemas and restores it after — the top-level schema keeps the ref while wrappers created during application do not claim it. Declaration order within a mode is preserved; a subclass overriding a validator NAME replaces the parent version entirely for both its modes.
**Probe:** `tests/test_validators.py::test_overridden_root_validators` :1811-1846 — child overriding both before+after validators yields exactly `[('B','pre'), ('B','post')]`, parent versions gone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "apply_model_validators inner outer model_schema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-point split (before-inside-input-schema, after/wrap-outside-serialized-model) and pop/restore-ref discipline; adapt mode partition names to your host; omit root-model and TypedDict special cases unless you port them too.
