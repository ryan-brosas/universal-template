<!-- capsule-v2 -->
# Version-UUID cache invalidation — how does a schema change invalidate cached generated models across processes, including linked tables?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** What is the full invalidation chain from "a field changed" to "every worker rebuilds the model"?

## invalidate_table_in_model_cache version bump + local sweep
**Path/Symbol:** `backend/src/baserow/contrib/database/table/cache.py:invalidate_table_in_model_cache` (71–87); entry-point hooks `fields/models.py:Field.invalidate_table_model_cache` (265–266) and `Field.save` (286–291); local-cache wildcard delete `core/cache.py:LocalCache.delete` (76–96).
**Signature:** `invalidate_table_in_model_cache(table_id: int) -> None`.
**Data Shape:** Redis cache entries are keyed `full_table_model_{id}_{BASEROW_VERSION}` and validated against a per-row `Table.version` TEXT column. Invalidation = new random UUID written to that row; stale entries die lazily on next read (`cache_entry["version"] == table.version` check), not by deletion.

### Decisive source
```python
def invalidate_table_in_model_cache(table_id: int):
    ...
    # Send signal for other potential cached values
    table_schema_changed.send(Table, table_id=table_id)

    # Delete model local cache
    local_cache.delete(f"database_table_model_{table_id}*")

    if settings.BASEROW_DISABLE_MODEL_CACHE:
        return None

    new_version = str(uuid.uuid4())
    # Make sure to invalidate ourselves and any directly connected tables.
    Table.objects_and_trash.filter(id=table_id).update(version=new_version)
```

**Flow:** field save/select-options-change → `Field.save()` ALWAYS calls invalidation (even for non-schema attribute writes — cheap by design) → signal `table_schema_changed` for auxiliary caches → request-local cache prefix-sweep (trailing `*` deletes every key starting with the prefix in the asgiref-Local dict; this kills BOTH `database_table_model_{id}` and the `_refreshed` latch) → UUID row update so all OTHER processes' Redis entries fail the version comparison.
**Invariant:** The version check happens against the freshly-read `table.version`, so invalidation must UPDATE THE ROW (any write works; content irrelevant) rather than delete Redis keys — deletion would race concurrent readers into re-caching stale attrs. Cross-table invalidation (link A→B bumps BOTH versions) is orchestrated by the field handlers, not this function; `test_table_cache.py::test_creating_link_row_field_invalidates_its_link_row_related_cache` (:11–34) pins exactly that plus unrelated-table version stability.
**Probe:** `grep -c "update(version=new_version)" backend/src/baserow/contrib/database/table/cache.py` → 1; `grep -n 'if key.endswith("*")' backend/src/baserow/core/cache.py` → line 89; direct tests `backend/tests/baserow/contrib/database/table/test_table_cache.py` (8 tests) cover create/convert/repoint/trash/restore/delete/disable-cache paths.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "invalidate table model cache version uuid", limit: 6 });
```

## Verdict
Adopt row-versioned lazy invalidation for any cross-process derived-artifact cache (no fan-out deletes needed); adapt to your ORM's signals; omit the BASEROW_DISABLE_MODEL_CACHE escape hatch unless you need CI determinism. Runner caveat: probe battery grep-executed at pin.
