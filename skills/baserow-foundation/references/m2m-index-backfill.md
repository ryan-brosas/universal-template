<!-- capsule-v2 -->
# m2m index backfill ladder — why does add_field need manual through-table FK indexes?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** Which code paths create m2m through-table indexes and why must they be re-checked at runtime?

## ensure_m2m_field_indexes + add_field override
**Path/Symbol:** `backend/src/baserow/contrib/database/db/schema.py:SafeBaserowPostgresSchemaEditor.add_field` (411–418), `ensure_m2m_field_indexes` (398–409), `ensure_single_column_index` (385–396).
**Signature:** `add_field(self, model, field)` → super() then `ensure_m2m_field_indexes(field)`; `ensure_single_column_index(model, field)` is idempotent (returns early if `_constraint_names(model, [column], index=True)` finds any backing index).
**Data Shape:** For an auto-created m2m through table, BOTH FK columns (`field.m2m_field_name()` forward and `m2m_reverse_field_name()` reverse) get single-column indexes.

### Decisive source
```python
def add_field(self, model, field):
    return_value = super().add_field(model, field)
    # Using the `create_model` to create a Baserow table, like what we do on
    # `import_serialize` does actually create the indexes of the through table.
    # However, when using `add_field` it does not. The code below will make sure
    # that the needed indexes are created.
    self.ensure_m2m_field_indexes(field)
    return return_value

def ensure_single_column_index(self, model, field):
    # If any index/constraint exists that is backed by an index on exactly this
    # column, don't create another.
    if self._constraint_names(model, [field.column], index=True):
        return
    stmt = self._create_index_sql(model, fields=[field])
    self.execute(stmt, params=None)
```

**Flow:** Django's `create_model` builds through-table indexes; `add_field` does NOT — so a link field added to an existing table would leave the REVERSE FK unindexed (joins from the related side full-scan). The override closes that gap idempotently; historical tables predating the fix are caught by the `missing_m2m_indexes_added` Table latch (see system-column-ladder capsule) whose migration backfills them.
**Invariant:** Index creation must be CHECK-THEN-CREATE (any constraint backed by an index on exactly that column counts) because link-row through tables may already carry unique constraints serving the same column. Reverse-side index is called out in-source as "especially important".
**Probe:** `grep -n "def ensure_m2m_field_indexes" backend/src/baserow/contrib/database/db/schema.py` → line 398; `grep -c "already_created_through_table_names"`-style dedup lives at :323–343 for create_model. No dedicated upstream unit test file for schema.py beyond test_db_schema.py (noted as coverage caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "ensure m2m field indexes single column constraint names", limit: 6 });
```

## Verdict
Adopt idempotent check-then-create index laddering around ORM gaps; adapt detection to your introspection API; omit historical-latch backfill if you have no legacy fleet. Probes grep-executed at pin d1db1705.
