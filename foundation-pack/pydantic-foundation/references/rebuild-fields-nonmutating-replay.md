<!-- capsule-v2 -->
# Non-mutating field rebuild — how do deferred annotations complete later without corrupting shared FieldInfo?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When `model_rebuild()` (or another model's schema generation) finally resolves a forward ref, how is the incomplete FieldInfo completed — in place or by replay?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_fields.py:rebuild_model_fields` (:584-636) + `_recreate_field_info` (:639-680).
**Signature:** `def rebuild_model_fields(cls, *, config_wrapper, ns_resolver, typevars_map) -> tuple[dict[str, FieldInfo], PydanticExtraInfo | None]` / `def _recreate_field_info(field_info, ns_resolver, typevars_map, *, lenient: bool) -> FieldInfo`.
**Data Shape:** Returns a NEW fields dict; complete fields pass through by reference, incomplete ones are rebuilt from scratch. Raises `NameError` in strict mode when an annotation still can't evaluate.

### Decisive source
```python
# rebuild_model_fields — note:
# This function *doesn't* mutate the model fields in place, as it can be called during
# schema generation, where you don't want to mutate other model's fields.
with ns_resolver.push(cls):
    for f_name, field_info in cls.__pydantic_fields__.items():
        if field_info._complete:
            rebuilt_fields[f_name] = field_info
        else:
            new_field = _recreate_field_info(field_info, ..., lenient=False)
            update_field_from_config(config_wrapper, f_name, new_field)
            rebuilt_fields[f_name] = new_field
```
```python
# _recreate_field_info
if lenient:
    ann = _generics.replace_types(field_info._original_annotation, typevars_map)
    ann, evaluated = _typing_extra.try_eval_type(ann, *ns_resolver.types_namespace)
else:
    # Not the best pattern, maybe we could ship our own `eval_type()`,
    # that would replace the type variables on the fly during evaluation.
    ann = _typing_extra.eval_type(field_info._original_annotation, *ns_resolver.types_namespace)
    ann = _generics.replace_types(ann, typevars_map)
    ann = _typing_extra.eval_type(ann, *ns_resolver.types_namespace)   # second eval!
    evaluated = True

if (assign := field_info._original_assignment) is PydanticUndefined:
    new_field = FieldInfo_.from_annotation(ann, _source=AnnotationSource.CLASS)
else:
    new_field = FieldInfo_.from_annotated_attribute(ann, assign, ...)
    new_field._original_assignment = assign
new_field._original_annotation = ann
# The description might come from the docstring if `use_attribute_docstrings` was `True`:
new_field.description = new_field.description if new_field.description is not None else existing_desc
if not evaluated:
    new_field._complete = False
```

**Flow:** push the class onto the NsResolver frame stack → per field: skip complete ones, else REPLAY the stored `(annotation, assignment)` origin pair into a brand-new FieldInfo → re-apply config (title/alias generators) → also rebuild incomplete `__pydantic_extra_info__` (eval → replace_types → eval again). The original FieldInfo object is never patched.
**Invariant:** Rebuild is side-effect-free on other models' fields because it runs mid-schema-generation of unrelated classes. Strict mode must eval → substitute TypeVars → RE-eval: stringified generic parameters only become resolvable after substitution.
**Probe:** `tests/test_fields.py::test_rebuild_model_fields_preserves_description` (:198-213) pins replay + attribute-docstring description survival across `model_rebuild()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "rebuild_model_fields recreate field info lenient", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt replay-from-original-pair over in-place mutation, and the double-eval ordering in strict mode. Adapt the lenient/strict flag to your host's deferred-resolution vocabulary. Omit the PydanticExtraInfo special case if your host lacks typed-extra support.
