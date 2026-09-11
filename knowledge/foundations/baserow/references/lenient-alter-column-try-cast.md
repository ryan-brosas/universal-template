<!-- capsule-v2 -->
# Lenient alter-column try_cast — how does Baserow change a user column's Postgres type without ever failing on uncastable data?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** When a field type changes and existing cell values can't be cast to the new type, why doesn't the ALTER TABLE fail?

## Lenient schema editor try_cast function lifecycle
**Path/Symbol:** `backend/src/baserow/contrib/database/db/schema.py:PostgresqlLenientDatabaseSchemaEditor._alter_field` (44–107) + `_alter_column_type_sql` (109–118); SQL templates in `db/sql_queries.py:1–29`.
**Signature:** `_alter_field(self, model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict=False)`; context manager `lenient_schema_editor(alter_column_prepare_old_value=None, alter_column_prepare_new_value=None, force_alter_column=False)`.
**Data Shape:** Inputs are Django old/new model fields for the SAME physical column (`field_{id}`). The editor synthesizes a per-column plpgsql function named `<column>_try_cast(text, int) returns <new_type>` whose body runs `alter_column_prepare_old_value`, then `alter_column_prepare_new_value`, then `p_in::<type>`, and on ANY exception returns `p_default` (NULL).

### Decisive source
```python
sql_alter_column_type = (
    "ALTER COLUMN %(column)s TYPE %(type)s%(collation)s "
    f"USING {TRY_CAST_FUNCTION_PLACEHOLDER}(%(column)s::text)"
)
...
if old_type != new_type:
    ...
    try_cast_function = self._try_cast_function_name(new_field)
    self.execute(sql_drop_field_try_cast % {"function_name": try_cast_function})
    self.execute(sql_create_field_try_cast % {...}, variables)
result = super()._alter_field(...)
if try_cast_function is not None:
    # The cast function is for one-time use only. We want to drop it
    # immediately after because we don't want to have millions of functions
    # lingering at some point.
    self.execute(sql_drop_field_try_cast % {"function_name": try_cast_function})
```

**Flow:** type change detected (`old_type != new_type`) → drop stale `{col}_try_cast` → create it from `sql_create_field_try_cast` embedding both prepare statements (`$FUNCTION$` stripped from variable values) → Django's normal `_alter_field` runs `ALTER COLUMN ... USING {col}_try_cast(col::text)` (placeholder replaced in `_alter_column_type_sql`) → drop the function again.
**Invariant:** The try_cast function is created and dropped around EVERY single alter; a porter who skips either DROP leaks one plpgsql function per column rename forever. Failure inside the cast returns NULL (`p_default`) — conversion never aborts the migration. `force_alter_column` fakes a type mismatch by appending `_forced` to `old_type` (:55–56) so an ALTER runs even when types match.
**Probe:** `grep -c "TRY_CAST_FUNCTION_PLACEHOLDER" backend/src/baserow/contrib/database/db/schema.py` → `3`; `grep -n "exception when others" backend/src/baserow/contrib/database/db/sql_queries.py` → line 13; direct test `backend/tests/baserow/contrib/database/db/test_db_schema.py::test_lenient_schema_editor` pins attribute propagation and SchemaEditorClass restore.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "lenient schema editor alter column prepare old value", limit: 6 });
```

## Verdict
Adopt the create→use→drop per-column try_cast pattern and never-fail cast semantics for any runtime user-schema engine; adapt the prepare-SQL hooks to your own field-type registry; omit the pg_temp variants in `sql_queries.py` (legacy path). Direct-test caveat: pytest runner unavailable in inspo clone (no venv) — probe verified by byte-exact grep against pin.
