<!-- capsule-v2 -->
# annotation-layer-permission-gate — How do you gate annotation-layer records behind a read permission without leaking layer existence?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A chart request can embed arbitrary annotation-layer ids — how do you serve their records only to users who may read annotations, and what happens when an id does not exist?

## Native annotation permission gate
**Path/Symbol:** `superset/common/query_context_processor.py` — `QueryContextProcessor.get_native_annotation_data` (:662-707), dispatched from `get_annotation_data` (:649-660).
**Signature:** `get_native_annotation_data(query_obj: QueryObject) -> dict[str, Any]` (staticmethod).
**Data Shape:** input layers: `{sourceType, name, value}` dicts; only `sourceType == "NATIVE"` handled here; output keyed by layer name: `{"columns": [start_dttm, end_dttm, short_descr, long_descr, json_metadata], "records": [...]}`; failures are typed `QueryObjectValidationError`.

### Decisive source
```python
layer_ids = [layer["value"] for layer in annotation_layers]
# Enforce the annotation read permission before returning layer records.
if layer_ids and not security_manager.can_access("can_read", "Annotation"):
    raise QueryObjectValidationError(
        _("You don't have access to annotation layers")
    )
layer_objects = {
    layer_object.id: layer_object
    for layer_object in AnnotationLayerDAO.find_by_ids(layer_ids)
}
...
# A request may reference a layer id that does not exist; treat it
# as a validation error rather than failing on the missing key.
if (layer_object := layer_objects.get(layer_id)) is None:
    raise QueryObjectValidationError(
        _("Annotation layer with ID %(layer_id)s was not found", layer_id=layer_id)
    )
```

**Flow:** filter NATIVE layers → if any ids present AND caller lacks `can_access("can_read", "Annotation")` ⇒ raise BEFORE any DAO lookup → batch-load all layers in one `find_by_ids` → per layer: missing id ⇒ typed validation error (not KeyError); records projected through the fixed 5-column whitelist.
**Invariant:** The permission check must precede the DAO call (a denied caller learns nothing about which ids exist); the check must be skipped only when there are zero native layers (empty requests stay free); unknown ids surface as validation errors naming the id, never as unhandled KeyErrors or silent drops.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:2402-2422` pins denied ⇒ `QueryObjectValidationError`, `can_access` called exactly once with `("can_read", "Annotation")`, and `find_by_ids` NOT called. Integration: `tests/integration_tests/charts/data/api_tests.py:995-1032` pins the positive path — interval + event layers returned, formula layer excluded from `annotation_data`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "get_native_annotation_data can_read Annotation find_by_ids", limit: 10 });
```

## Verdict
Adopt check-before-lookup ordering, the empty-request bypass, batched id lookup, typed missing-id errors, and column-whitelist projection; adapt the permission predicate to your host's authorization API; omit Superset's specific `AnnotationLayerDAO`/bakeable model plumbing. Coverage: processor read at :620-772 (completing pass-1 full read); both direct tests read at cited ranges; MCP disconnected this pass — Retrieve is a documented target.
