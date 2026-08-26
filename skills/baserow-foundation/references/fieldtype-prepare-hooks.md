<!-- capsule-v2 -->
# FieldType alter-column prepare hooks — how does a field type inject data-conversion SQL into a type change?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** What contract must `get_alter_column_prepare_old_value` / `_new_value` follow so the lenient editor converts cells correctly?

## FieldType SQL-hook pair
**Path/Symbol:** `backend/src/baserow/contrib/database/fields/registries.py:FieldType.get_alter_column_prepare_old_value` (672–694) and `.get_alter_column_prepare_new_value` (696–720); exemplars `field_types.py` DateFieldType :1414/:1449 (timezone/text munging), NumberFieldType :1011 (REGEXP_REPLACE non-digits), RatingFieldType :1040.
**Signature:** `get_alter_column_prepare_{old,new}_value(self, connection, from_field, to_field) -> Optional[str]` — a PL/pgSQL fragment operating on variable `p_in`, executed INSIDE the per-column try_cast function body; may return a `(sql, variables_dict)` TUPLE for parameterized SQL (`$FUNCTION$` markers stripped from values).
**Data Shape:** old-hook reshapes `p_in` to TEXT the new cast understands; new-hook normalizes text before `p_in::new_type`; returning None means "no preparation".

### Decisive source
```python
def get_alter_column_prepare_old_value(self, connection, from_field, to_field):
    """
    Can return an SQL statement to convert the `p_in` variable to a readable text
    format for the new field.
    This SQL will not be run when converting between two fields of the same
    baserow type which share the same underlying database column type.
    If you require this then implement force_same_type_alter_column.

    Example: return "p_in = lower(p_in);"
    """
    return None
```

**Flow:** update_field detects type/model-field change → `lenient_schema_editor(from_type.prepare_old(connection, old, new), to_type.prepare_new(...), force_alter_column)` → fragments spliced into try_cast body (`alter_column_prepare_old_value` then `..._new_value` then cast) → uncastable survivors become NULL. Same-basetype conversions skip ALTER unless `force_same_type_alter_column` is True or handler forces it (`force_alter_column = True` whenever `baserow_field_type_changed`, fields/handler.py:718–722).
**Invariant:** Hooks must be pure SQL fragments valid inside a plpgsql function's BEGIN block — no COMMIT, no DDL. They run PER ROW during table rewrite: cost scales with row count. The tuple-with-variables form exists because some conversions need bound params (e.g., timezone names) that can't be inlined safely.
**Probe:** `grep -c "force_alter_column = True" backend/src/baserow/contrib/database/fields/handler.py` → 1; `grep -n "def get_alter_column_prepare_old_value" backend/src/baserow/contrib/database/fields/registries.py` → line 672; graph retrieval rank-1 resolves `registries.py 672-694` line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "lenient schema editor alter column prepare old value", limit: 6 });
```

## Verdict
Adopt declarative per-type conversion-SQL hooks instead of imperative row-by-row migration scripts; adapt variable-binding convention to your DB driver; omit force-alter semantics if your types never share physical column types. Runner caveat: probes grep-executed at pin d1db1705.
