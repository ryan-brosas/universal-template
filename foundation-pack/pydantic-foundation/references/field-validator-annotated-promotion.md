<!-- capsule-v2 -->
# Field-validator Annotated promotion — do `@field_validator`s become function schemas directly or ride the metadata stream?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When building a field's core schema, where exactly do `@field_validator` decorators enter, and what ordering guarantees hold against Annotated metadata?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generate_schema.py:_common_field_schema` (:1270-1330), `_mode_to_validator` :165-167, `filter_field_decorator_info_by_field` :214-217, `check_decorator_fields_exist` :187-210; `functional_validators.py:AfterValidator._from_decorator` :86-87 (twins on Before/Plain/Wrap).
**Signature:** `_mode_to_validator: dict[FieldValidatorModes, type[BeforeValidator | AfterValidator | PlainValidator | WrapValidator]] = {'before': BeforeValidator, 'after': AfterValidator, 'plain': PlainValidator, 'wrap': WrapValidator}`.
**Data Shape:** input `(name, field_info, decorators)` → `(CoreSchema, core_metadata)`; decorator infos filtered per field name.

### Decisive source
```python
# _common_field_schema:
if decorators.field_validators:
    validators_from_decorators = [
        _mode_to_validator[decorator.info.mode]._from_decorator(decorator)
        for decorator in filter_field_decorator_info_by_field(decorators.field_validators.values(), name)
    ]
else:
    validators_from_decorators = []

with self.field_name_stack.push(name):
    schema = self._apply_annotations(
        source_type,
        annotations + validators_from_decorators,   # appended AFTER Annotated metadata
    )
...
# default wraps OUTSIDE all validators:
if not field_info.is_required():
    schema = wrap_default(field_info, schema)

def check_validator_fields_against_field_name(info, field) -> bool:
    fields = info.fields
    return '*' in fields or field in fields
```

**Flow:** per field → filter class-level validator infos by name (`*` wildcard matches all) → convert each to its Annotated-metadata validator class via `_from_decorator` (only `.func` is carried; mode is encoded by the CLASS chosen) → append to the annotation list so `_apply_annotations` applies them in declaration order after type metadata → wrap default last.
**Invariant:** v2 field validators ride the SAME pipeline as `Annotated[..., AfterValidator]` — ordering between Annotated validators and decorators follows list append order — while the v1 plane (`decorators.validators`, root validators, `each_item`) uses `apply_validators`/`apply_each_item_validators` and any `always=True` forces `field_info.validate_default=True`. Field existence checks skip `'*'` and `check_fields=False`.
**Probe:** `tests/test_validators.py::test_wildcard_validators` :730-761 pins exact call order (`check_a` before wildcard for field a); `tests/test_validators.py::test_field_validator_input_type_invalid_mode` :3000-3010 pins `json_schema_input_type` + `mode='after'` rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "_common_field_schema filter_field_decorator_info_by_field _mode_to_validator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt converting decorator infos into first-class metadata objects applied through one annotation pipeline; adapt `_from_decorator` payloads to your metadata classes; omit the v1 `always`/`each_item` compatibility shims when porting a clean-room design.
