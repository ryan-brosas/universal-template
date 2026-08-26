<!-- capsule-v2 -->
# Alias generator priority gate — when does a config `alias_generator` override an explicit alias?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** Under what priority conditions does the model-level alias generator overwrite (or skip) an alias declared on the field, and why does priority 1 matter for inheritance?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_fields.py:update_field_from_config` (:223-237) → `_apply_alias_generator_to_field_info` (:173-220).
**Signature:** `def update_field_from_config(config_wrapper, field_name, field_info) -> None` / `def _apply_alias_generator_to_field_info(alias_generator: Callable[[str], str] | AliasGenerator, field_name: str, field_info: FieldInfo)`.
**Data Shape:** Mutates `field_info.alias / validation_alias / serialization_alias / alias_priority` in place; called from `collect_model_fields` per complete field and again per rebuilt field in `rebuild_model_fields`.

### Decisive source
```python
# Apply an alias_generator if
# 1. An alias is not specified
# 2. An alias is specified, but the priority is <= 1
if (
    field_info.alias_priority is None
    or field_info.alias_priority <= 1
    or field_info.alias is None
    or field_info.validation_alias is None
    or field_info.serialization_alias is None
):
    alias, validation_alias, serialization_alias = None, None, None
    if isinstance(alias_generator, AliasGenerator):
        alias, validation_alias, serialization_alias = alias_generator.generate_aliases(field_name)
    elif callable(alias_generator):
        alias = alias_generator(field_name)
        if not isinstance(alias, str):
            raise TypeError(f'alias_generator {alias_generator} must return str, not {alias.__class__}')
    # if priority is not set, we set to 1
    # which supports the case where the alias_generator from a child class is used
    # to generate an alias for a field in a parent class
    if field_info.alias_priority is None or field_info.alias_priority <= 1:
        field_info.alias_priority = 1
    # if the priority is 1, then we set the aliases to the generated alias
    if field_info.alias_priority == 1:
        ...
```

**Flow:** title generator first (`field_title_generator` — per-field overrides config), then alias generator → gate on `alias_priority is None or <= 1` OR any unset alias slot → AliasGenerator produces a (validation, serialization, alias) triple, plain callables a single alias coalesced via `get_first_not_none` → generated aliases stamped with priority **1**, so any subclass's generator re-runs over inherited fields.
**Invariant:** An explicit `Field(alias=...)` carries priority ≥2 and always beats the generator; a generator-produced alias is deliberately weak (priority 1) so child-class config can regenerate parent fields. A non-str return from the generator is a hard TypeError.
**Probe:** `tests/test_aliases.py::test_alias_generator_with_alias` (:694-702) and `test_low_priority_alias` (:315-334) pin generator-vs-explicit priority; `test_alias_override_behavior` (:151-193) pins child alias override dropping parent constraints while keeping the type hint; `tests/test_model_signature.py::test_use_field_name` (:96-102) pins `validate_by_name` fallback at the signature layer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "pydantic", function_name: "update_field_from_config", direction: "both", depth: 2 });
```

## Verdict
Adopt the two-tier alias-priority gate and the stamp-generated-aliases-as-priority-1 trick that makes generators inheritable. Adapt `AliasGenerator` triple dispatch to your host's config surface. Omit `get_first_not_none` plumbing if you only support single-callable generators.
