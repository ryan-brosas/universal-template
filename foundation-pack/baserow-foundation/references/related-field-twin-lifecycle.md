<!-- capsule-v2 -->
# Related-field twin lifecycle — when is the reverse link-row field created, moved, or deleted?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** What are the exact hook sites where the mirror LinkRowField in the related table is managed, and what invariants keep the pair consistent?

## after_create / before_schema_change / after_update / after_delete twin management
**Path/Symbol:** `backend/src/baserow/contrib/database/fields/field_types.py:LinkRowFieldType` — `before_create` (3210–3256), `after_create` (3312–3337), `find_next_unused_related_field_name` (3340–3349), `before_schema_change` (3351–3438), `after_update` (3440–3477), `after_delete` (3479–3485).
**Signature:** hooks receive `(field|from_field, to_field, model(s), user, connection, ...)`; twin creation always via `FieldHandler().create_field(..., type_name=self.type, skip_django_schema_editor_add_field=False, link_row_table=..., link_row_related_field=..., link_row_relation_id=<same id>, skip_search_updates=True)`.
**Data Shape:** Twin existence tracked by `LinkRowField.link_row_related_field_id`; API flag `has_related_field` defaults to `not self_referencing` when unset (:3255–3256).

### Decisive source
```python
# before_create
self_referencing_link_row = table.id == link_row_table.id
create_related_field = field_kwargs.get("has_related_field")
if self_referencing_link_row and create_related_field:
    raise SelfReferencingLinkRowCannotHaveRelatedField(...)
if create_related_field is None:
    field_kwargs["has_related_field"] = not self_referencing_link_row

# before_schema_change — four quadrants of (from_has_related, to_has_related):
if from_link_row_table_has_related_field and not to_link_row_table_has_related_field:
    FieldHandler().delete_field(..., delete_strategy=DeleteFieldStrategyEnum.DELETE_OBJECT)
    if to_instance:
        to_field.link_row_related_field = None
elif to_instance and from_instance:
    ...
    from_field.link_row_related_field.name = related_field_name
    from_field.link_row_related_field.link_row_table = to_field.table
    FieldHandler().move_field_between_tables(
        from_field.link_row_related_field, to_field.link_row_table)
```

**Flow:** create → after_create spawns twin with next-unused name (`{other_table}` then `{other} - {field}`, else numeric suffix) sharing relation id → retarget (`link_row_table` changed, both sides still want twins) → twin is MOVED between tables (name/order updated, then `move_field_between_tables`) and `to_field.link_row_related_field` re-pointed at the MOVED instance so later reads aren't stale → drop-related on one side deletes ONLY the twin with `DELETE_OBJECT` strategy (prevents recursive delete of the field mid-loop) → deleting a link field deletes its twin in `after_delete`.
**Invariant:** A self-referencing link can never carry a related field (would need a second m2m on the same pair). Permission checks for creating/deleting twins run against the RELATED workspace context inside these hooks. The stale-instance fix at :3434–3438 is load-bearing: `from_field.link_row_related_field` was mutated, so `to_field` must adopt the same instance.
**Probe:** `grep -c "link_row_relation_id=" backend/src/baserow/contrib/database/fields/field_types.py | head -1` counts threaded ids (sites :3334/:3416/:3474); direct tests: `test_self_referencing_link_row_raise_if_link_row_table_has_related_field_is_set` (:1722), `test_link_row_can_change_link_from_same_table_to_another_table_and_back` (:1572).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "link row related field create move between tables", limit: 6 });
```

## Verdict
Adopt explicit twin-entity lifecycle hooks around create/update/delete of relation-bearing entities; adapt naming fallback ladder; omit DELETE_OBJECT strategy nuance if your delete path has no re-entrancy. Tests read at pin; runner blocked honestly.
