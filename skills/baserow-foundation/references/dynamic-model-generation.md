<!-- capsule-v2 -->
# Dynamic table model generation — how does one Postgres table per user table become a live Django model without polluting the app registry?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** How is a Django model class built at request time for an arbitrary user table, and what registry hygiene keeps it isolated from static models?

## Table._get_model type() choreography
**Path/Symbol:** `backend/src/baserow/contrib/database/table/models.py:Table._get_model` (956–1166), `_fetch_and_generate_field_attrs` (1219–1345), `GeneratedModelAppsProxy` (662–762), `patch_meta_get_field` (765–786).
**Signature:** `_get_model(fields=None, field_ids=None, field_names=None, attribute_names=False, manytomany_models=None, add_dependencies=True, managed=False, use_cache=True, app_label=None) -> Type[GeneratedTableModel]`.
**Data Shape:** Returns a NEW unmanaged (`managed=False`) class named `Table{id}Model` backed by physical table `database_table_{id}`. Field attrs come from `field_set(manager="objects_and_trash")` — TRASHED FIELDS ARE INCLUDED because their columns still exist; omitting them makes `objects.create()` send NULLs and violate NOT NULL constraints. Attribute names default to `field_{id}` (never user names unless `attribute_names=True`, where duplicates get renamed `{name}_{db_column}`).

### Decisive source
```python
if app_label is None:
    # Generate a unique app_label to make the generation of the model thread
    # safe. Related fields generate pending operations in the `apps`
    # registry, but they're identified by the model class name. If the same
    # model is generated at the same time, the pending operations can be
    # executed in a wrong order. A unique app_label isolates in that case.
    app_label = str(uuid.uuid4()) + "_database_table"
...
model = type(
    str(model_name),
    (
        GeneratedTableModel,
        TrashableModelMixin,
        CreatedAndUpdatedOnMixin,
        models.Model,
    ),
    attrs,
)
patch_meta_get_field(model._meta)
if not manytomany_models:
    self._after_model_generation(attrs, model)
```

**Flow:** unique per-call app_label (thread safety) → Meta with `GeneratedModelAppsProxy` as apps + collision-safe `(order,id)` index name → fetch fields incl. trashed (+ same-table dependencies when filtered) → per-field `field_type.get_model_field(...)` builds attrs dict → `type()` the class → patch `_meta.get_field` fallback that lazily calls `after_model_generation` for m2m fields → `_after_model_generation` adds link-row/m2m relations via the proxy.
**Invariant:** Generated models are NEVER registered in Django's global apps registry — `GeneratedModelAppsProxy.register_model` diverts them into `self.baserow_models`, runs `do_all_pending_operations()` (max_iterations=3: one op can enqueue another) so relation resolution completes WITHOUT the memory leak of lingering `_pending_operations`, then deletes the residual empty `apps.all_models[label]` key. The proxy's `get_models` must return static apps' models PLUS all generated ones or Django's reverse-relation graph breaks.
**Probe:** `grep -c 'app_label = str(uuid.uuid4()) + "_database_table"' backend/src/baserow/contrib/database/table/models.py` → 1; direct tests `test_table_models.py::test_no_pending_operations_after_creating_self_linking_model`-equivalent lives in `backend/tests/baserow/contrib/database/field/test_link_row_field_type.py:1701` asserting `len(apps._pending_operations) == 0`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "get_model generated table model app_label uuid apps proxy", limit: 6 });
```

## Verdict
Adopt dynamic `type()` model generation with per-generation unique app_label and a diverting apps-proxy for any user-defined-schema product; adapt attribute naming/dedup rules to your column grammar; omit Django-specific pending-operation plumbing only if your ORM has no global registry. Runner caveat: probes grep-verified; behavior additionally pinned by upstream test source.
