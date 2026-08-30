<!-- capsule-v2 -->
# `complete_model_class` — what runs after fields exist, and how do failures degrade to mocks instead of raising?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** In what order are core schema, validator, serializer, signature, and the completion flag produced — and which failures are absorbed with `set_model_mocks` vs raised?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_model_construction.py:complete_model_class` (:561-682).
**Signature:** `def complete_model_class(cls, config_wrapper, ns_resolver, *, raise_errors: bool = True, call_on_complete_hook: bool = True, create_model_module: str | None = None, is_force_rebuild: bool = False) -> bool`.
**Data Shape:** Returns False on any swallowed failure (fields still incomplete, undefined annotation, `InvalidSchemaError`); True only when validator+serializer+signature are installed and `__pydantic_complete__=True`.

### Decisive source
```python
if not cls.__pydantic_fields_complete__:
    # Note: when coming from `ModelMetaclass.__new__()`, this results in fields being built twice.
    # ... we rebuild here [to raise the NameError for the specific undefined annotation]:
    try:
        cls.__pydantic_fields__, cls.__pydantic_extra_info__ = rebuild_model_fields(...)
    except NameError as e:
        exc = PydanticUndefinedAnnotation.from_name_error(e)
        set_model_mocks(cls, f'`{exc.name}`' if exc.name is not None else None)
        if raise_errors:
            raise exc from e

gen_schema = GenerateSchema(config_wrapper, ns_resolver, typevars_map)
try:
    schema = gen_schema.generate_schema(cls)
except PydanticUndefinedAnnotation as e:
    if raise_errors: raise
    set_model_mocks(cls, f'`{e.name}`' ...)
    return False
...
cls.__pydantic_core_schema__ = schema
cls.__pydantic_validator__ = create_schema_validator(schema, ..., _use_prebuilt=not is_force_rebuild)
cls.__pydantic_serializer__ = SchemaSerializer(schema, core_config, _use_prebuilt=not is_force_rebuild)
cls.__signature__ = LazyClassAttribute('__signature__', partial(generate_pydantic_signature, init=cls.__init__, fields=cls.__pydantic_fields__, ...))
cls.__pydantic_complete__ = True
if call_on_complete_hook:
    cls.__pydantic_on_complete__()
return True
```

**Flow:** rebuild fields if incomplete (to surface WHICH name is undefined) → generate core schema for the class itself → `cleaning` happens in GenerateSchema; on failure → mocks + False → recompute `__pydantic_computed_fields__` AFTER schema gen (property return types now evaluated) → `set_deprecated_descriptors` → install core schema → build validator via plugin-aware `create_schema_validator` (`_use_prebuilt=False` forces fresh build on force-rebuild) → serializer → LAZY `__signature__` via `LazyClassAttribute` (class-level attr only, never instance) → set `__pydantic_complete__=True` → optional on-complete hook.
**Invariant:** The three mockable slots (`__pydantic_core_schema__/validator/serializer`) are replaced atomically at the END; every earlier failure path installs mocks and returns False rather than leaving a half-built model. `raise_errors=False` is the metaclass default so import-time stays quiet.
**Probe:** `grep -n "def test_deferred_core_schema" tests/test_main.py` (:3625 — pins the deferred/mock completion behavior end-to-end).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "complete_model_class set_model_mocks generate schema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering (schema → computed-fields refresh → deprecated descriptors → validator/serializer → lazy signature → flag) and the mocks-on-failure contract; adapt `LazyClassAttribute` to your host's descriptor toolkit; omit pydantic-core `_use_prebuilt` caching specifics.
