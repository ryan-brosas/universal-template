<!-- capsule-v2 -->
# Signature parameter merge — how is the synthesized `__signature__` built when a custom `__init__` exists?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** Which parameters come from the custom init, which from fields, how do aliases and invalid identifiers resolve, and when does `**extra_data` appear?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_signature.py:generate_pydantic_signature` (:166-190) + `_generate_signature_parameters` (:82-163) + `_field_name_for_signature` (:27-45).
**Signature:** `def generate_pydantic_signature(init, fields, validate_by_name, extra: ExtraValues | None, is_dataclass=False) -> inspect.Signature`.
**Data Shape:** Installed lazily by `complete_model_class` via `LazyClassAttribute('__signature__', partial(...))`, so signature construction cost is paid on first `inspect.signature()`/help() use, not at class creation.

### Decisive source
```python
for param in islice(present_params, 1, None):  # skip self arg
    if fields.get(param.name):
        if getattr(fields[param.name], 'init', True) is False:
            continue                              # exclude params with init=False
        param = param.replace(name=_field_name_for_signature(param.name, fields[param.name]))
    if param.kind is param.VAR_KEYWORD:
        var_kw = param
        continue
    merged_params[param.name] = param

if var_kw:  # if custom init has no var_kw, fields which are not declared in it cannot be passed through
    allow_names = validate_by_name
    for field_name, field in fields.items():
        param_name = _field_name_for_signature(field_name, field)   # alias → validation_alias → name
        if field_name in merged_params or param_name in merged_params:
            continue
        if not is_valid_identifier(param_name):
            if allow_names: param_name = field_name
            else:
                use_var_kw = True
                continue                                 # invalid identifier rides **kwargs instead
        default = Parameter.empty if field.is_required() else (
            _HAS_DEFAULT_FACTORY if field.default_factory is not None else field.default)
        merged_params[param_name] = Parameter(param_name, Parameter.KEYWORD_ONLY,
                                              annotation=field.rebuild_annotation(), default=default)

if extra == 'allow':
    use_var_kw = True

if var_kw and use_var_kw:
    default_model_signature = [('self', Parameter.POSITIONAL_ONLY), ('data', Parameter.VAR_KEYWORD)]
    if [(p.name, p.kind) for p in present_params] == default_model_signature:
        var_kw_name = 'extra_data'       # standard model signature gets the friendly name
    else:
        var_kw_name = var_kw.name
    while var_kw_name in fields:         # generate a name that's definitely unique
        var_kw_name += '_'
    merged_params[var_kw_name] = var_kw.replace(name=var_kw_name)
```

**Flow:** start from the custom (or default) `__init__` params minus self → drop fields with `init=False`, rename surviving ones by alias priority → only when the init has `**kwargs`, append every remaining field as KEYWORD_ONLY with `<factory>` sentinel for default_factory (`_HAS_DEFAULT_FACTORY`, copied from stdlib dataclasses) → `extra='allow'` forces the kwarg through; its final name avoids collision by appending underscores.
**Invariant:** A custom init WITHOUT `var_kw` suppresses undeclared fields from the signature entirely (they can't be passed); alias renaming requires a VALID Python identifier or falls back to the field name under `validate_by_name=True`, otherwise to `**extra_data`.
**Probe:** `tests/test_model_signature.py::test_model_signature` (:26-35, `(*, a: float, b: int = 10, c: int = <factory>) -> None`), `test_custom_init_signature` (:50-69, merged custom+field+alias params), `test_invalid_identifiers_signature` (:86-93, alias vs `**extra_data`), `test_extra_allow_no_conflict` (:114-120).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "generate_pydantic_signature signature parameters model", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the merge ladder (custom-init first, fields fill gaps only through var_kw) plus the `<factory>` sentinel and underscore-uniquening. Adapt `_HAS_DEFAULT_FACTORY` to your host's repr conventions. Omit the dataclass-only `_process_param_defaults` pass unless your host models FieldInfo-carrying defaults directly in `__init__`.
