<!-- capsule-v2 -->
# DecoratorInfos MRO rebind — how are validators inherited across pydantic AND non-pydantic bases without mutating them?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** How does a subclass collect `@field_validator`/`@computed_field` decorators from parents (including plain classes), and what gets written back onto which class?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_decorators.py:DecoratorInfos.build` (:430-509) + `_decorator_infos_for_class` (:528-575) + `Decorator.build` (:231-270).
**Signature:** `@classmethod def build(cls, typ: type[Any], replace_wrapped_methods: bool = True) -> Self`.
**Data Shape:** Seven ordered dicts keyed by class-namespace var name (`validators`, `field_validators`, `root_validators`, `field_serializers`, `model_serializers`, `model_validators`, `computed_fields`). Note: keys are function names, NOT field names.

### Decisive source
```python
# reminder: dicts are ordered and replacement does not alter the order
res = cls()
# Iterate over the bases, without the actual `typ`.
for base in reversed(mro(typ)[1:-1]):
    existing: DecoratorInfos | None = base.__dict__.get('__pydantic_decorators__')
    if existing is None:
        existing, _ = _decorator_infos_for_class(base, cls_ref=lambda: '', collect_to_replace=False)
    res.validators.update({k: v.bind_to_cls(typ, cls_ref()) for k, v in existing.validators.items()})
    ...  # six more families, same pattern
decorator_infos, to_replace = _decorator_infos_for_class(typ, cls_ref=cls_ref, collect_to_replace=True)
res.validators.update(decorator_infos.validators)  # ...
if replace_wrapped_methods and to_replace:
    for name, value in to_replace:
        setattr(typ, name, value)      # unwrap: PydanticDescriptorProxy → raw function on OWNED classes
res._validate()                        # one field serializer per field, else 'multiple-field-serializers'
```
and the rebind path:
```python
func = get_attribute_from_bases(cls_, cls_var_name)
if shim is not None: func = shim(func)
func = unwrap_wrapped_function(func, unwrap_partial=False)
...
return Decorator(cls_ref=cls_ref, cls_var_name=cls_var_name, func=func, shim=shim, info=info)
# bind_to_cls -> self.build(cls, ..., info=copy(self.info))
```

**Flow:** walk MRO bottom-up excluding `typ` itself and `object` → reuse each base's cached `__pydantic_decorators__` when present, else scan the bare base's `vars()` for `PydanticDescriptorProxy`-wrapped members WITHOUT caching anything on it → re-fetch each decorator's function through `get_attribute_from_bases` and rebuild with a COPIED info bound to `typ` → collect own-class decorators last (subclass overrides parent by name, dict order preserved) → `setattr` unwrapped methods back only onto classes pydantic owns.
**Invariant:** Parent classes — pydantic or not — are read-only inputs: no `__pydantic_decorators__` is stamped on them and their decorator `info` objects are copied before child config mutates titles/serializations. The single-field-serializer uniqueness check runs per assembled set.
**Probe:** `tests/test_decorators.py::test_plain_class_not_mutated` (:114-125) pins "bare parent stays unstamped"; `test_decorator_info_not_mutated` (:128-139) pins child-config title generation touching only the child's copied info.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "DecoratorInfos build decorator field validator positions unwrap", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt MRO-order collection with copy-on-rebind and owned-class-only method replacement. Adapt the `PydanticDescriptorProxy` marker to your host's decorator-carrying convention; any descriptor wrapper with `.decorator_info`/`.wrapped` semantics works. Omit V1 shims (`shim=`) and TypedDict support if absent.
