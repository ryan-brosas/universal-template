<!-- capsule-v2 -->
# SerialField relation-id allocation — how do both sides of a link share ONE physical through table without racing?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** Where does `link_row_relation_id` come from and why is a DB sequence used instead of an app-level counter?

## SerialField nextval pre_save
**Path/Symbol:** `backend/src/baserow/contrib/database/fields/fields.py:SerialField` (266–293); consumer `fields/models.py:LinkRowField.link_row_relation_id` (:515) + `through_table_name` (:533–545).
**Signature:** `SerialField(models.IntegerField)` with `db_returning=True`; `pre_save(model_instance, add)` returns `RawSQL("nextval('{table}_{field}_seq'::regclass)")` when adding with a falsy value.
**Data Shape:** The sequence `database_databasefield_link_row_relation_id_seq` must be created MANUALLY by migration (`0071_alter_linkrowfield_link_row_relation_id` is the in-repo example). Value allocation happens inside Postgres, independent of the surrounding transaction.

### Decisive source
```python
class SerialField(models.IntegerField):
    """
    The serial field works very similar compared to the `AutoField` ...
    The sequence is independent of a transaction to prevent race conditions.
    Please, ensure to create the sequence manually in the database before using
    this field. Look at the migration `0071_alter_linkrowfield_link_row_relation_id`
    for an example.
    """
    db_returning = True

    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.name):
            sequence_name = self.get_sequence_name(
                model_instance._meta.db_table, self.name)
            return RawSQL(f"nextval('{sequence_name}'::regclass)", ())
        return super().pre_save(model_instance, add)
```

**Flow:** create LinkRowField → Django INSERT fires pre_save → `nextval()` reserves id R (never rolled back) → field row persists with `link_row_relation_id=R` → through table name resolves to `database_relation_{R}` → `after_create` creates the twin related field passing `link_row_relation_id=field.link_row_relation_id` explicitly (field_types.py:3334) so BOTH rows resolve `through_table_name` to the SAME physical table.
**Invariant:** Never allocate relation ids from application state (max(id)+1 races under concurrent field creation; rolled-back transactions would double-allocate). The reverse-field creation calls MUST thread the same relation id through — every site does it verbatim (`grep 'link_row_relation_id=' field_types.py` shows :3334/:3416/:3474). `unique=False` on the column is deliberate: many fields legitimately share one relation id.
**Probe:** `grep -n "nextval('{sequence_name}'::regclass)" backend/src/baserow/contrib/database/fields/fields.py` → line 289; `grep -n 'return f"{self.THROUGH_DATABASE_TABLE_PREFIX}{self.link_row_relation_id}"' backend/src/baserow/contrib/database/fields/models.py` → line 545.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "link row relation id through table name serial", limit: 6 });
```

## Verdict
Adopt DB-sequence-backed shared-identifier allocation for any co-owned derived structure; adapt prefix grammar (`database_relation_`) to your naming scheme; omit `IntegerWithSequence` variant unless you hit bulk_update cast issues (see fields.py:315 comment). Probe grep-executed at pin; runner unavailable.
