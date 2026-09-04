<!-- capsule-v2 -->
# Dataclass-fields collection twin — how do stdlib `__dataclass_fields__` become pydantic FieldInfos without double-collecting inherited fields?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When collecting a (pydantic or stdlib) dataclass's fields, how are MRO, ClassVars, init-vars, and unevaluated annotations handled compared to BaseModel?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_fields.py:collect_dataclass_fields` (:683-788) + `rebuild_dataclass_fields` :791-834; `pydantic/_internal/_dataclasses.py:set_dataclass_fields` (:65-82).
**Signature:** `collect_dataclass_fields(cls: type[StandardDataclass], *, config_wrapper, ns_resolver=None, typevars_map=None) -> dict[str, FieldInfo]`.
**Data Shape:** ordered dict name→FieldInfo; `_original_assignment` holds either a pydantic FieldInfo (Field-as-default case) or the raw `dataclasses.Field`.

### Decisive source
```python
for base in reversed(cls.__mro__):
    if not dataclasses.is_dataclass(base):
        continue
    with ns_resolver.push(base):
        for ann_name, dataclass_field in dataclass_fields.items():   # INHERITED dict
            base_anns = _typing_extra.safe_get_annotations(base)
            if ann_name not in base_anns:
                # `__dataclass_fields__` contains every field, even the ones from base classes.
                continue                                             # only defining base collects it
            ...
            if _typing_extra.is_classvar_annotation(ann_type):
                continue
            if (not dataclass_field.init and dataclass_field.default is dataclasses.MISSING
                    and dataclass_field.default_factory is dataclasses.MISSING):
                continue
            if isinstance(dataclass_field.default, FieldInfo_):
                if dataclass_field.default.init_var:
                    if dataclass_field.default.init is False:
                        raise PydanticUserError(..., code='clashing-init-and-init-var')
                    continue                                          # init_var fields skipped entirely
                field_info = FieldInfo_.from_annotated_attribute(ann_type, dataclass_field.default, _source=AnnotationSource.DATACLASS)
                field_info._original_assignment = dataclass_field.default
            else:
                field_info = FieldInfo_.from_annotated_attribute(ann_type, dataclass_field, _source=AnnotationSource.DATACLASS)
                field_info._original_assignment = dataclass_field
            if not evaluated:
                field_info._complete = False
                field_info._original_annotation = ann_type
```

**Flow:** walk reversed MRO → per defining base push its namespace → filter the shared `__dataclass_fields__` dict by "annotation declared on THIS base" so each field is collected exactly once → skip ClassVar / init=False-no-default / init_var fields → build FieldInfo via the SAME `from_annotated_attribute(…, _source=DATACLASS)` used for models, storing the original assignment for replay → typevars applied post-hoc (`apply_typevars_map`) → optional attribute-docstring harvest with frame inspection DISABLED for stdlib dataclasses (`use_inspect=not hasattr(cls,'__is_pydantic_dataclass__')`).
**Invariant:** replay symmetry — `rebuild_dataclass_fields` re-runs `from_annotated_attribute(original_annotation, _original_assignment)` into a FRESH dict (never mutating live fields mid-schema-generation), re-applying config and carrying docstring descriptions; class-attr fixup setattr's the default only when the class attribute is still a FieldInfo.
**Probe:** `tests/test_dataclasses.py::test_rebuild_dataclass` :2598-2618 pins rebuild None/raise/True tri-state and `_types_namespace` injection; `::test_init_vars_inheritance` :2414+ pins init_var semantics across inheritance.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "collect_dataclass_fields set_dataclass_fields rebuild_dataclass_fields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the define-once MRO filter over the inherited fields dict and the non-mutating replay contract; adapt `AnnotationSource.DATACLASS` gating to your metadata validator; omit stdlib-dataclass frame-inspection fallbacks if you only support pydantic dataclasses.
