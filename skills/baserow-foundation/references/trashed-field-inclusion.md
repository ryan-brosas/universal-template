<!-- capsule-v2 -->
# Trashed-field model inclusion — why must trashed columns stay on the generated Django model?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** When a field is soft-deleted, what happens to its physical column and how does model generation keep INSERTs working?

## objects_and_trash field fetch + attribute dedup
**Path/Symbol:** `backend/src/baserow/contrib/database/table/models.py:_fetch_and_generate_field_attrs` (1219–1345, decisive comment 1237–1243) + manager pair `TableModelManager` (468–470, filters `trashed=False`) vs `TableModelTrashAndObjectsManager` (454–465).
**Signature:** fields fetched via `self.field_set(manager="objects_and_trash").select_related("table__database__workspace", "content_type")`; trashed entries land in `attrs["_trashed_field_objects"]` keyed by id while their MODEL FIELD is still added under `field.db_column`.
**Data Shape:** `_field_objects` (visible) vs `_trashed_field_objects` (hidden-but-present); `get_field_objects(include_trash)` chains both.

### Decisive source
```python
# Construct a query to fetch all the fields of that table. We need to
# include any trashed fields so the created model still has them present
# as the column is still actually there. If the model did not have the
# trashed field attributes then model.objects.create will fail as the
# trashed columns will be given null values by django triggering not null
# constraints in the database.
fields_query = (
    self.field_set(manager="objects_and_trash")
    .select_related("table__database__workspace", "content_type")
    .all()
)
```

**Flow:** trash a field (`delete_field` → `schema_editor.remove_field`? NO — trash keeps the column; only permanent trash purge runs DDL at trash_types.py:305–310) → next `get_model()` includes it via objects_and_trash manager → its attr exists so Django INSERTs supply proper defaults/NULLs per field type → API/serialization paths iterate ONLY `_field_objects`, making trashed cells invisible without schema surgery.
**Invariant:** Soft-delete ≠ drop-column: dropping on trash would make restore impossible AND require locking DDL per trash op. Under `attribute_names=True`, name collisions with trashed siblings rename to `{name}_{db_column}` / `trashed_{name}` (:1306–1321) — a porter who skips this produces duplicate attrs that silently shadow.
**Probe:** `grep -cn 'field_attrs[replaced_field_name\] = field_attrs.pop(field_name)' backend/src/baserow/contrib/database/table/models.py` → 1; direct test coverage: `test_table_cache.py::test_trashing_link_row_field_invalidates_its_related_tables_cache` + `::test_restoring_...` pin version bumps on trash/restore; permanent-drop path lives in `trash/trash_types.py:305`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "trashed field objects and trash generated model", limit: 6 });
```

## Verdict
Adopt keep-the-column soft delete for user-schema products; adapt visibility filtering to your serializer layer; omit duplicate-name renaming if you forbid same-name fields. Runner caveat: probes grep-executed at pin d1db1705.
