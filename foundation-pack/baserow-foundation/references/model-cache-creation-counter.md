<!-- capsule-v2 -->
# Model-cache creation_counter bump — why does serving a cached model's field attrs require advancing Django's global field counter?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** When a generated model's fields are restored from Redis cache, how are Django field-equality collisions prevented?

## creation_counter cache-restoration guard
**Path/Symbol:** `backend/src/baserow/contrib/database/table/models.py:1093–1134` (cache-hit branch of `_get_model`) + `backend/src/baserow/contrib/database/table/cache.py:38–54`.
**Signature:** `get_cached_model_field_attrs(table) -> Optional[Dict]` / `set_cached_model_field_attrs(table, field_attrs)`; cache key `full_table_model_{table_id}_{BASEROW_VERSION}` with entry `{"field_attrs", "version"}`.
**Data Shape:** Cache stores the RAW attrs dict (Django model-field instances pickled). On hit, every restored field carries its ORIGINAL `creation_counter`; any subsequently created live model field gets a fresh counter from the global class attribute.

### Decisive source
```python
# We found cached model fields, they will have a cached creation_counter
# attribute each used to compare model fields to do django
# fundamental internal operations like generating SQL to select from this
# table. Any new model fields added to this table will use a global
# static counter on the Model class itself. To prevent any possibility
# of collisions between the model fields that just came out of the cache
# and these new model fields we are about to init below, we increase
# this global creation_counter to prevent any possible collision and
# horrible bugs.
max_creation_counter_from_cache = DjangoModelFieldClass.creation_counter
for f in field_attrs.values():
    if isinstance(f, DjangoModelFieldClass) and not f.auto_created:
        max_creation_counter_from_cache = max(...)
DjangoModelFieldClass.creation_counter = max_creation_counter_from_cache + 1

# We have to add the order field after reading the potentially cached values ...
field_attrs["order"] = models.DecimalField(max_digits=40, decimal_places=20, ...)
```

**Flow:** default-kwargs calls only → refresh `table.version` once per session (`local_cache` "refreshed" key) → Redis hit returns attrs (skips the whole field query) → bump global counter past every cached value → THEN add the synthetic `order` DecimalField so it is constructed with a non-colliding counter.
**Invariant:** The counter bump must happen BEFORE constructing any new model field on this model — otherwise two fields compare equal via `Field.__eq__` (counter-only), Django silently drops one from SELECT lists, and every row access re-queries per-cell as if deferred. `use_cache` is only allowed when `fields=[]`, no `field_ids`, `add_dependencies=True`, `attribute_names=False`, and not `BASEROW_DISABLE_MODEL_CACHE`. Direct test `test_table_models.py::test_model_coming_out_of_cache_queries_correctly` (:1120–1188) forces `Field.creation_counter=0`, caches, then asserts no duplicate counters, 0-query row reads, and both columns present in compiled SQL.
**Probe:** `grep -n "DjangoModelFieldClass.creation_counter = max_creation_counter_from_cache + 1" backend/src/baserow/contrib/database/table/models.py` → line 1122; `grep -n '"version": table.version' backend/src/baserow/contrib/database/table/cache.py` → line 52.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "invalidate table model cache version uuid", limit: 6 });
```

## Verdict
Adopt versioned caching of serialized schema artifacts plus an explicit identity-counter guard when the framework compares objects by creation order; adapt the invalidation signal (see capsule-map sibling); omit Redis specifics for in-process hosts. Caveat: behavioral test read at pin, not executed (no runner).
