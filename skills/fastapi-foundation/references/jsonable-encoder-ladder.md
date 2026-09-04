<!-- capsule-v2 -->
# jsonable_encoder fallback ladder — What is the exact conversion order for arbitrary objects, and where do custom encoders, include/exclude, and the _sa hack apply?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** Given any return object (model, dataclass, dict, set, generator, arbitrary class), what does `jsonable_encoder` produce and in which precedence?

## Recursive encoder with type-table fallback
**Path/Symbol:** `fastapi/encoders.py:jsonable_encoder` (129–366) + `ENCODERS_BY_TYPE` (84–112) + `encoders_by_class_tuples` (115–126) + `decimal_encoder` (59–81).
**Signature:** `jsonable_encoder(obj, include=None, exclude=None, by_alias=True, exclude_unset=False, exclude_defaults=False, exclude_none=False, custom_encoder=None, sqlalchemy_safe=True) -> Any`.
**Data Shape:** returns JSON-safe structures; `include/exclude` normalize to set/dict then apply ONLY to BaseModel dumps and dict traversal — NOT to list items.

### Decisive source
```python
    if isinstance(obj, BaseModel):
        obj_dict = obj.model_dump(mode="json", include=..., exclude=..., by_alias=by_alias,
                                  exclude_unset=..., exclude_none=..., exclude_defaults=...)
        return jsonable_encoder(obj_dict, exclude_none=exclude_none, exclude_defaults=...,
                                sqlalchemy_safe=sqlalchemy_safe)   # NOTE: include/exclude DROPPED
    ...
    if type(obj) in ENCODERS_BY_TYPE:
        return ENCODERS_BY_TYPE[type(obj)](obj)
    for encoder, classes_tuple in encoders_by_class_tuples.items():
        if isinstance(obj, classes_tuple):
            return encoder(obj)
    if is_pydantic_v1_model_instance(obj):
        raise PydanticV1NotSupportedError(...)
    try:    data = dict(obj)
    except Exception as e:
        errors = [e]
        try:    data = vars(obj)
        except Exception as e2:
            errors.append(e2); raise ValueError(errors) from e
```

**Flow:** custom_encoder exact-type first, then isinstance scan → BaseModel dump → dataclass asdict → Enum.value → PurePath str → scalars passthrough → PydanticUndefined→None → dict walk (keys encoded too; `_sa*` keys dropped when sqlalchemy_safe; None dropped under exclude_none) → iterables (list/set/frozenset/generator/tuple/deque ALL become list) → ENCODERS_BY_TYPE exact match → subclass-tuple table (built once at import so one encoder serves many types) → v1-model refusal → last resort `dict(obj)` then `vars(obj)` else ValueError aggregating BOTH errors.
**Invariant:** (1) The model-dump recursion intentionally drops include/exclude for nested content — they've already been applied by pydantic; re-passing them would corrupt nested filtering. (2) `Decimal` encodes as int when exponent ≥ 0 else float (`decimal_encoder`) to keep integer Decimals round-trippable. (3) Sets are unordered but encode positionally to lists — porters relying on stable output must pre-sort.
**Probe:** `tests/test_jsonable_encoder.py` covers every rung incl. subclasses, dataclasses, generators, `_sa` removal, and include/exclude matrix.
