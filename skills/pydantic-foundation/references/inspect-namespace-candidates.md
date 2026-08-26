<!-- capsule-v2 -->
# Namespace inspection candidates — how are field defaults vs private attrs vs ignored names classified before the class exists?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What exact rules decide whether a namespace entry becomes a field candidate, a private attribute, or an ignored name — and why must private attributes be DELETED from the namespace?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_model_construction.py:inspect_namespace` (:397-496).
**Signature:** `def inspect_namespace(namespace, ignored_types, *, base_class_vars: set[str], base_class_fields: set[str]) -> ModelNamespaceInfo`.
**Data Shape:** Returns `ModelNamespaceInfo(private_attributes, ignored_names, ignored_types, private_candidates, field_candidates, base_field_names, model_config_assigned)`. Mutates its input: deletes recognized private attributes from `namespace`.

### Decisive source
```python
for var_name, value in namespace.items():
    if var_name == 'model_config' or var_name == '__pydantic_extra__':
        continue
    elif (isinstance(value, type) and value.__module__ == namespace['__module__']
          and value.__qualname__.startswith(f'{namespace["__qualname__"]}.')):
        continue                      # nested class defined here; don't error
    elif isinstance(value, all_ignored_types) or value.__class__.__module__ == 'functools':
        ignored_names.add(var_name)   # functions/properties/cached partials etc.
        continue
    elif isinstance(value, ModelPrivateAttr):
        if var_name.startswith('__'): raise PydanticUserError(...)      # no dunder privates
        elif is_valid_field_name(var_name): raise PydanticUserError(...) # must be sunder (_name)
        private_attributes[var_name] = value
    elif isinstance(value, FieldInfo) and not is_valid_field_name(var_name):
        raise PydanticUserError(... suggested_name = var_name.lstrip('_') ...)  # no underscore fields
    elif var_name.startswith('__'):
        continue
    elif is_valid_privateattr_name(var_name):
        private_candidates.append(var_name)   # may STILL become a field/classvar after annotations evaluate
    elif var_name in base_class_vars:
        continue
    else:
        field_candidates.append(var_name)

for var_name in private_attributes:
    del namespace[var_name]     # explicit ModelPrivateAttr values must NOT land on the class
```

**Flow:** iterate raw class-body assignments in order; classify by VALUE type first (`ModelPrivateAttr`, `FieldInfo`, ignored types), then by NAME shape (dunder skip, sunder→private candidate, base class-var skip, else field candidate). Final field-vs-private-vs-ClassVar resolution is deferred to `collect_model_fields` because `ClassVar[...]`/plain-annotation truth is only knowable once annotations are evaluated.
**Invariant:** Candidates are LISTS in insertion order — field order in errors/signatures follows class-body order. Private attributes assigned as `ModelPrivateAttr(...)` are removed from the namespace so they never become class attributes; annotation-only underscore names stay (resolved later from `__private_attributes__`). `default_ignored_types()` is `@cache`d and includes both `typing_extensions.TypeAliasType` and (3.12+) `typing.TypeAliasType`.
**Probe:** `grep -c "code='class-not-fully-defined'" pydantic/_internal/_mock_val_ser.py` pins the sibling mock plane; for THIS seam: `grep -n 'private_candidates.append' pydantic/_internal/_model_construction.py` (single :477 site proves classification-before-resolution).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "inspect_namespace private candidates field candidates", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the classify-by-value-then-name ladder and the namespace-deletion rule; adapt the `PydanticUserError` messages/codes; omit v1-compat concerns. Porters who skip the deletion step ship classes whose private attr DEFAULT objects leak as class attributes.
