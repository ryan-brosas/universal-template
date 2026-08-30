<!-- capsule-v2 -->
# Link-row twin m2m after_model_generation — why does a link field contribute TWO ManyToManyFields and how does recursion terminate?

**Source:** Baserow MIT `develop@d1db1705`; Codebase Memory `ext-baserow`. **Question:** How are forward and reverse link-row relations attached to generated models without infinite model-generation loops?

## after_model_generation twin-field choreography
**Path/Symbol:** `backend/src/baserow/contrib/database/fields/field_types.py:LinkRowFieldType.after_model_generation` (3078–3127) + `get_model_field` (3070–3076); recursion guard `table/models.py:GeneratedModelAppsProxy.register_model` + `do_all_pending_operations`.
**Signature:** `after_model_generation(self, instance, model, field_name) -> None`; m2m kwargs always `{null=True, blank=True, db_table=instance.through_table_name, db_constraint=False}`.
**Data Shape:** The FORWARD m2m is contributed to the current model under `field_{id}` (db_column); the REVERSE direction exists as a separate LinkRowField row in the related table whose model attribute is discovered by scanning `related_model._field_objects` for a field whose `link_row_related_field_id == instance.id`, else defaults to synthetic name `reversed_field_{instance.id}`.

### Decisive source
```python
def get_model_field(self, instance, **kwargs):
    """
    A model field is not needed because the ManyToMany field is going to be added
    after the model has been generated.
    """
    return None
...
model.baserow_models[model_name] = model   # register SELF first — breaks recursion

if instance.is_self_referencing:
    related_model = model
else:
    related_model = model.baserow_models.get(related_model_name)
    if related_model is None:
        related_model = instance.link_row_table.get_model(
            manytomany_models=model.baserow_models,
            app_label=model._meta.app_label,
        )
        model.baserow_models[related_model_name] = related_model
...
models.ManyToManyField(
    to=related_model,
    related_name=related_name,
    null=True, blank=True,
    db_table=instance.through_table_name,
    db_constraint=False,
).contribute_to_class(model, field_name)
```

**Flow:** `get_model_field` returns None (placeholder so the column count matches) → after the class exists, self-register into `baserow_models` → resolve/generate the related table's model WITHIN THE SAME app_label and shared `manytomany_models` dict (this is the recursion terminator) → attach ONE ManyToManyField pointing at the related model; the reverse side is the OTHER field's own m2m, both declaring the SAME physical through table (`database_relation_{link_row_relation_id}`).
**Invariant:** Both sides must declare `db_constraint=False` and identical `db_table` or Postgres gets two through tables / FK checks on user data. Self-referencing links reuse `model` itself and NEVER have a related field (`SelfReferencingLinkRowCannotHaveRelatedField`, pinned by test :1722 in `test_link_row_field_type.py`). Pending operations from these m2m constructions MUST be flushed via the proxy (max 3 iterations) or they leak memory per generation — pinned by `test_no_pending_operations_after_creating_self_linking_model` (:1701).
**Probe:** `grep -n 'model.baserow_models[model_name] = model' backend/src/baserow/contrib/database/fields/field_types.py` → line 3083; `grep -c 'related_name = f"reversed_field_{instance.id}"' backend/src/baserow/contrib/database/fields/field_types.py` → 3 (LinkRow/MultiSelect/Collaborators share the idiom).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-baserow", query: "after_model_generation many to many related model baserow_models", limit: 6 });
```

## Verdict
Adopt deferred relation attachment (return-None placeholder + post-class hook) for any ORM that can't add relations mid-construction; adapt the shared-through-table naming to your prefix grammar; omit the apps-proxy pending-op flush only if your framework has no global registry. Tests read at pin; runner blocked honestly.
