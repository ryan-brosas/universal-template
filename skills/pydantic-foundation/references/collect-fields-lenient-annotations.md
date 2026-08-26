<!-- capsule-v2 -->
# Lenient field collection — how does a model collect fields without failing on forward references?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When a class-body annotation cannot be evaluated yet, what is stored, what is copied from parents, and why are assigned field attributes deleted off the class?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_fields.py:collect_model_fields` (:277-581).
**Signature:** `def collect_model_fields(cls, config_wrapper, ns_resolver, *, typevars_map=None, namespace_info=None) -> tuple[dict[str, FieldInfo], PydanticExtraInfo | None, set[str], dict[str, ModelPrivateAttr]]`.
**Data Shape:** Called only by `set_model_fields` / `ModelMetaclass.__new__`. Returns fields dict (body order), optional `__pydantic_extra__` info, class-var names, private attrs. Never raises for unevaluated annotations — it defers.

### Decisive source
```python
type_hints = _typing_extra.get_model_type_hints(cls, ns_resolver=ns_resolver)
...
for ann_name, (ann_type, evaluated) in type_hints.items():
    ...
    if assigned_value is PydanticUndefined:  # no assignment, just a plain annotation
        if ann_name in cls_annotations or ann_name not in parent_fields_lookup:
            field_info = FieldInfo_.from_annotation(ann_type, _source=AnnotationSource.CLASS)
            field_info._original_annotation = ann_type
            if not evaluated:
                field_info._complete = False
        else:
            # The field was present on one of the (possibly multiple) base classes, we make a copy directly from it.
            parent_field_info = parent_fields_lookup[ann_name]._copy()
            if typevars_map:
                field_info = _recreate_field_info(parent_field_info, ..., lenient=True)
            else:
                field_info = parent_field_info
    ...
    # attributes which are fields are removed from the class namespace:
    # 1. To match the behaviour of annotation-only fields
    # 2. To avoid false positives in the NameError check above
    try:
        delattr(cls, ann_name)
    except AttributeError:
        pass  # indicates the attribute was on a parent class
```

**Flow:** build `parent_fields_lookup` from `reversed(bases)` → evaluate all type hints once (`get_model_type_hints`) → per hint: ClassVar ⇒ class_vars; invalid field name ⇒ maybe private attr; deprecated BaseModel methods (`dict`, `schema`, …) detected **by identity** via `@cache`d `id()` frozensets and reset to `PydanticUndefined`; then either fresh FieldInfo (storing `_original_annotation`, `_complete=False` when unevaluated), parent copy (+lenient recreate under `typevars_map`), or `from_annotated_attribute(ann_type, assigned_value)` storing BOTH `_original_assignment` and `_original_annotation` → `delattr` the assignment off the class → apply `update_field_from_config` only when `_complete`.
**Invariant:** Collection never fails on a forward ref: an unevaluated hint still yields a FieldInfo marked `_complete=False` carrying its original annotation/assignment for later replay (`rebuild_model_fields`). Field defaults must never remain visible as class attributes.
**Probe:** `tests/test_fields.py::test_rebuild_model_fields_preserves_description` (:198-213) pins the incomplete-then-rebuild replay end-to-end; `tests/test_main.py::test_default_factory` (:1733-1767) pins default handling through collection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "collect_model_fields rebuild_model_fields decorators signature generation", limit: 15, fields: ["signature", "lines"] });
```

## Verdict
Adopt the lenient-collect-then-replay split, parent-copy inheritance of FieldInfo, identity-based deprecated-method detection, and the post-collection `delattr`. Adapt error codes (`model-field-missing-annotation`, `model-field-overridden`) to your host's error taxonomy. Omit pydantic's `import_cached_field_info()` import-cycle plumbing.
