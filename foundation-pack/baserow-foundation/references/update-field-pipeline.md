<!-- capsule-v2 -->
# update_field alter pipeline — what is the exact ordering of hooks, converters, and schema edits when a field changes?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** In what order does FieldHandler.update_field run permission checks, model regeneration, converter lookup, ALTER, and dependency updates — and why can't the order change?

## update_field orchestration
**Path/Symbol:** `backend/src/baserow/contrib/database/fields/handler.py:FieldHandler.update_field` (501–854).
**Signature:** `update_field(user, field, new_type_name=None, return_updated_fields=False, postfix_to_fix_name_collisions=None, after_schema_change_callback=None, **kwargs) -> field | (field, updated_fields)`; raises `CannotChangeFieldType` wrapping `ProgrammingError/DataError`.
**Data Shape:** Requires a SPECIFIC field instance (`type(field) is Field` → ValueError :543–547). `old_field = deepcopy(field)` BEFORE polymorphic type flip. Two generated models bracket the DDL: `from_model = table.get_model(field_ids=[], fields=[field])` (:557) and `to_model = ...` (:669).

### Decisive source
```python
if baserow_field_type_changed:
    ViewHandler().before_field_type_change(field)
    dependants_broken_due_to_type_change = (
        from_field_type.get_dependants_which_will_break_when_field_type_changes(
            field, to_field_type, field_cache))
    new_model_class = to_field_type.model_class
    field.change_polymorphic_type_to(new_model_class)
...
field.save(field_cache=field_cache, raise_if_invalid=True)
...
from_field_type.before_schema_change(old_field, field, ...)
converter = field_converter_registry.find_applicable_converter(from_model, old_field, field)
if converter:
    converter.alter_field(old_field, field, from_model, to_model,
                          from_model_field, to_model_field, user, connection)
else:
    with lenient_schema_editor(...prepare_old..., ...prepare_new..., force_alter_column) as schema_editor:
        schema_editor.alter_field(from_model, from_model_field, to_model_field)
altered_column = from_model_field_type != to_model_field_type   # db_parameters comparison
to_field_type.after_update(...)
```

**Flow:** permission → snapshot old → generate from_model → resolve types/broken-dependents → polymorphic ctype flip → validate+prepare values → before_update → save metadata (fires invalidation) → rebuild dependencies → db_index compatibility gate → generate to_model → mark type-changed dependants in collector → before_schema_change (twin management) → converter-or-lenient ALTER → compute `altered_column` from `db_parameters()["type"]` strings → after_update → callback → cache_model_fields → walk broken dependants → apply collector updates → `_update_dependencies_of_field_updated` → signals + search-data scheduling.
**Invariant:** The metadata row is saved BEFORE the schema edit so the version-UUID invalidation is already visible if the process dies mid-alter; `after_update` runs even when only constraints changed (`field_constraints_changed` participates in the same gates). Converter short-circuit means lenient editor is the FALLBACK, not the default path.
**Probe:** `grep -n "old_field = deepcopy(field)" backend/src/baserow/contrib/database/fields/handler.py` → line 555 precedes `change_polymorphic_type_to` at :612; direct test file `backend/tests/baserow/contrib/database/field/test_field_handler.py` exercises conversion matrices.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "update field alter column converter schema change handler", limit: 6 });
```

## Verdict
Adopt the two-model bracket + hook ladder for any typed-schema evolution engine; adapt converter registry granularity; omit polymorphic content-type mechanics if your storage is single-table inheritance free. Runner blocked in clone; order verified against source lines cited above.
