<!-- capsule-v2 -->
# ModelField adapter over TypeAdapter — How does FastAPI wrap Pydantic v2 so validation errors carry request locations?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What does the v2 compat layer's `ModelField` own, and why is its `__hash__` identity-based?

## _compat/v2.ModelField
**Path/Symbol:** `fastapi/_compat/v2.py:class ModelField` (114–244; validate 173–188, serialize 190–213, serialize_json 215–239) + `get_schema_from_model_field` (254–282) + `get_definitions` (285–346); factory in `fastapi/utils.py:create_model_field` (58–77).
**Signature:** `ModelField(field_info: FieldInfo, name: str, mode: Literal["validation","serialization"] = "validation", config=None)` (dataclass); `validate(value, values={}, *, loc=()) -> tuple[Any, list[dict]]`.
**Data Shape:** builds ONE `TypeAdapter(Annotated[annotation, *metadata, Field(**attributes)])` in `__post_init__` (asdict-rebuild needed on pydantic ≥ 2.12 to dodge UnsupportedFieldAttributeWarning) — this adapter is the single validation/serialization engine per field.

### Decisive source
```python
    def validate(self, value, values={}, *, loc=()):
        try:
            return (self._type_adapter.validate_python(value, from_attributes=True), [])
        except ValidationError as exc:
            return None, _regenerate_error_with_loc(
                errors=exc.errors(include_url=False), loc_prefix=loc)

    def __hash__(self) -> int:
        # Each ModelField is unique for our purposes, to allow making a dict from
        # ModelField to its JSON Schema.
        return id(self)
```

**Flow:** errors are RETURNED not raised — callers aggregate across params/deps before deciding to raise `RequestValidationError` → `_regenerate_error_with_loc` prefixes pydantic's nested locs with the request location (`("body", alias)` etc.) → serialization mode picked by `field.mode` ("validation" fields read validation_alias, "serialization" read serialization_alias — see `get_schema_from_model_field`) → schema generation runs ONCE per app via `get_definitions`, keyed by `(field, mode)` in `field_mapping`; identity hash makes that dict possible since two structurally identical fields must keep distinct schemas when aliases differ.
**Invariant:** (1) Never raise from `validate` — the two-tuple contract IS the error-aggregation design. (2) Identity-hash means ModelField instances must not be recreated casually per request; caches like `get_cached_model_fields` exist precisely to reuse them. (3) `create_model_field` translates `PydanticSchemaGenerationError` into the actionable FastAPIError hint (response_model=None advice) and refuses pydantic.v1 models outright.
**Probe:** `tests/test_dependency_utils.py` and the error-shape suites (`tests/test_multi_body_errors.py`) pin returned-error locs; `tests/test_compat.py` pins adapter behavior.
