<!-- capsule-v2 -->
# Generated-system-column ladder — which extra columns does every generated model conditionally carry and who guards their migration?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** How do `order`, `created_by`, `last_modified_by`, `needs_background_update`, and the field-rules state column get added to generated models, and why are they gated by boolean Table flags?

## Table feature-flag columns
**Path/Symbol:** `backend/src/baserow/contrib/database/table/models.py` — `_get_model` additions (1124–1145), `_add_created_by`/`_add_last_modified_by` (1175–1195, using `IgnoreMissingForeignKey` with `db_constraint=False, on_delete=DO_NOTHING`), `_add_needs_background_update_column` (1168–1173); flag columns on `Table` (:872–908 incl. `missing_m2m_indexes_added` db_default=False/default=True comment block); physical backfill at `table/handler.py:896–911`; names in `table/constants.py`.
**Signature:** `field_attrs["order"] = models.DecimalField(max_digits=40, decimal_places=20, editable=False, default=1)`; each conditional add appends to BOTH `field_attrs` and (for order) `indexes`.
**Data Shape:** Physical columns `database_table_{id}.created_by / last_modified_by / needs_background_update` exist only for tables created/backfilled after those features shipped; the Table-row booleans (`created_by_column_added`, etc.) are per-table migration latches read on EVERY model generation.

### Decisive source
```python
# The m2m indexes of the foreign keys were not added before because the
# `schema_editor.add_field` does not add them. The `schema_editor.create_model`
# does add those. This problem has been addressed, but there are tables out there
# without those indexes.
missing_m2m_indexes_added = models.BooleanField(
    # The `db_default` must be false because this is used when an entry is created
    # no default value is set. ... However, if the field index changes are deployed,
    # this default value is used, and in that case, the index has been applied.
    db_default=False, default=True, ...)
```

**Flow:** generate model → always add synthetic `order` DecimalField (AFTER cache restoration — see creation-counter capsule) → check each latch → conditionally attach system columns → class built. New tables get latches set True; old tables are backfilled by handler code that regenerates the model with `use_cache=False` and ALTERs the columns in inside `safe_django_schema_editor(atomic=False)` (:899).
**Invariant:** NEVER assume a system column exists on a generated model — always gate reads/writes on the Table latch or use `fields_requiring_refresh_after_insert/update` helpers. The dual `db_default=False` + `default=True` pattern encodes deployment-order truth at INSERT time vs ORM time. System FKs deliberately skip constraints so deleting users never fails row writes across millions of user tables.
**Probe:** `grep -c "field_{self.id}" backend/src/baserow/contrib/database/fields/models.py` → 1 (db_column grammar); `grep -n 'return f"{USER_TABLE_DATABASE_NAME_PREFIX}{self.id}"' backend/src/baserow/contrib/database/table/models.py` → line 941; constants file pins all column-name strings (`LAST_MODIFIED_BY_COLUMN_NAME = "last_modified_by"`, etc.).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "created_by last_modified_by column added generated model", limit: 6 });
```

## Verdict
Adopt per-table feature-latch booleans when rolling out new physical columns across unbounded user-created tables; adapt latch mechanics to your migration runner; omit IgnoreMissingForeignKey if your DB tolerates enforced FKs at this scale. Probes grep-executed at pin d1db1705.
