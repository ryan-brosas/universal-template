<!-- capsule-v2 -->
# Config wrapper precedence ladder — in what order do config sources merge, and where do alias semantics get patched?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When a model class is created, which of bases / namespace / metaclass-kwargs wins for each config key, and what dynamic patching happens between the user-facing ConfigDict and the core config?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_config.py:ConfigWrapper.for_model` (:132-174), `ConfigWrapper.core_config` :188-238, `ConfigWrapper.__getattr__` :176-186, `prepare_config` :324-342, `_config_dict_to_core_config_key` :30-59, `config_defaults` :271-321.
**Signature:** `for_model(cls, bases: tuple[type, ...], namespace: dict[str, Any], kwargs: dict[str, Any]) -> Self`; `core_config(self, title: str | None) -> core_schema.CoreConfig`.
**Data Shape:** three input sources with descending priority (kwargs > namespace > bases); output is one flat ConfigDict; `core_config` maps it through a rename table into the pydantic-core config dict.

### Decisive source
```python
config_new = ConfigDict()
for base in bases:
    config = getattr(base, 'model_config', None)
    if config:
        config_new.update(config.copy())          # base order: later base wins

config_class_from_namespace = namespace.get('Config')
config_dict_from_namespace = namespace.get('model_config')
if config_class_from_namespace and config_dict_from_namespace:
    raise PydanticUserError('"Config" and "model_config" cannot be used together', code='config-both')
config_from_namespace = config_dict_from_namespace or prepare_config(config_class_from_namespace)
config_new.update(config_from_namespace)

for k in list(kwargs.keys()):
    if k in config_keys:
        config_new[k] = kwargs.pop(k)             # POPPED — config keys never leak as metaclass kwargs
return cls(config_new)
```
and in `core_config`:
```python
if (populate_by_name := config.get('populate_by_name')) is not None:
    if config.get('validate_by_name') is None:
        config['validate_by_alias'] = True
        config['validate_by_name'] = populate_by_name
if config.get('validate_by_alias') is False and config.get('validate_by_name') is None:
    config['validate_by_name'] = True
if (not config.get('validate_by_alias', True)) and (not config.get('validate_by_name', False)):
    raise PydanticUserError('At least one of `validate_by_alias` or `validate_by_name` must be set to True.',
                            code='validate-by-alias-and-name-false')
```

**Flow:** merge base `model_config` dicts in base order → namespace `model_config` overrides (class-based `Config` is the deprecated fallback, converted by a dir() scan of non-dunder attrs; both present ⇒ hard error) → metaclass kwargs override, restricted to known keys and removed from kwargs → at core-config time: empty dict takes a fast path, `populate_by_name` backports into the new validate_by_* pair when unset, alias-only-false forces name-validation on, both-false raises, then keys are renamed via the table (`extra`→`extra_fields_behavior`) and `title` is special-cased. Attribute reads fall back config_dict → module-level `config_defaults` → AttributeError, with `__getattr__` hidden from type checkers so typos are caught statically.
**Invariant:** every config key that arrives via kwargs is consumed (popped) — the metaclass never sees it again; the both-false alias check runs at CORE-CONFIG time (first schema build), not at class creation, so a bad config can sit dormant until use; `prepare_config` warns once for class-based configs but still converts them; defaults live in ONE module-level dict so `getattr(wrapper, k)` and `config_defaults[k]` can never disagree (a test enforces the annotation list matches).
**Probe:** `tests/test_config.py::test_config_and_module_config_cannot_be_used_together` :84-91 (PydanticUserError), `::test_multiple_inheritance_config` :490-518 (Child(Mixin, Parent) merges frozen+extra+use_enum_values+validate_by_name exactly per ladder), `::test_user_error_on_alias_settings` :990-996 (both-false error), `::test_populate_by_name_still_effective` :980-987 (backport lets both alias and name validate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "ConfigWrapper for_model core_config prepare_config validate_by_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-source descending-priority merge with pop-on-consume, the mutual-exclusion gate, and the deferred both-false alias check; adapt the deprecated class-based conversion window to your host's deprecation policy; omit the populate_by_name backport if your host has no legacy alias flag. Caveat: Retrieve written but not executed this pass (MCP unavailable); anchors verified by direct read at the pin.
