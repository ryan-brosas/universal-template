<!-- capsule-v2 -->
# Safe schema editor composition — why must Baserow never use Django's plain schema_editor for create/delete?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** How does Baserow wrap Django's schema editor so deferred-SQL crashes roll back cleanly AND self-referencing link-row m2m through-tables aren't created/deleted twice?

## safe_django_schema_editor dynamic subclass + atomic fix
**Path/Symbol:** `backend/src/baserow/contrib/database/db/schema.py:safe_django_schema_editor` (421–464), `_build_schema_editor_class` (283–291), `SafeBaserowPostgresSchemaEditor` (303–418), `optional_atomic` (294–300).
**Signature:** `safe_django_schema_editor(atomic=True, name=None, classes=None, **kwargs)` yields a composed editor; `lenient_schema_editor(...)` delegates to it with `classes=[PostgresqlLenientDatabaseSchemaEditor]`.
**Data Shape:** Builds `type(name, (*classes, connection.SchemaEditorClass), {})` at call time, swaps it onto the GLOBAL `connection.SchemaEditorClass`, and restores the original in `finally`. The editor is instantiated with `atomic=False`; transactionality is provided by an outer `transaction.atomic()`.

### Decisive source
```python
if not issubclass(regular_schema_editor, SafeBaserowPostgresSchemaEditor):
    # Only override the connections schema editor if we haven't already done it
    # in an outer safe schema editor context.
    BaserowSafeDjangoPostgresSchemaEditor = _build_schema_editor_class(
        name, classes
    )
    connection.SchemaEditorClass = BaserowSafeDjangoPostgresSchemaEditor

kwargs.setdefault("connection", connection)

try:
    with optional_atomic(atomic=atomic):
        with connection.SchemaEditorClass(atomic=False, **kwargs) as schema_editor:
            yield schema_editor
finally:
    connection.SchemaEditorClass = regular_schema_editor
```

**Flow:** guard against double-wrap (`issubclass` check — nested contexts reuse the outer swap) → compose class chain → global swap → run inside own atomic → restore original class even on exception.
**Invariant:** (1) The inner editor runs with `atomic=False` because Django's `BaseDatabaseSchemaEditor.__exit__` fails to exit its internal atomic when DEFERRED sql raises (index creation is deferred until after the CREATE TABLE statement) — the wrapper's explicit atomic fixes that leaked-savepoint bug; (2) `SafeBaserowPostgresSchemaEditor.create_model/delete_model` track already-created/deleted m2m through-table names in a set so a self-referencing LinkRowField's TWO ManyToManyField definitions sharing one `db_table` don't crash with "table already exists/gone"; (3) every table DDL in Baserow MUST go through this editor (table/handler.py:489 create, trash/trash_types.py:146/305 delete/remove, fields/handler.py:404 add).
**Probe:** `grep -c "TRY_CAST_FUNCTION_PLACEHOLDER" backend/src/baserow/contrib/database/db/schema.py` → 3 (file identity); direct tests `backend/tests/baserow/contrib/database/db/test_db_schema.py::test_safe_schema_editor` and `::test_lenient_schema_editor_is_also_safe` assert `savepoint_ids` return to baseline after a forced deferred-index ProgrammingError.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "safe django schema editor postgres create model many to many twice", limit: 6 });
```

## Verdict
Adopt "wrap the framework's schema editor with your own composed subclass + explicit outer atomic" for any engine doing runtime DDL; adapt the m2m-dedup set to how your relations share physical tables; omit the vendor-specific serial-sequence handling unless porting to Postgres. Test caveat: runner blocked in clone; savepoint assertions verified by reading test source at pin.
