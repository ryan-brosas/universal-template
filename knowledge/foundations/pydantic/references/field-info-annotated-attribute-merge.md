<!-- capsule-v2 -->
# Annotated ↔ assignment merge — in what order are `Annotated` metadata and an assigned `Field(...)` combined?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When a field is declared as `Annotated[T, meta...] = Field(...)`, whose metadata wins, where do plain defaults land, and what does the `Final` qualifier change?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/fields.py:FieldInfo.from_annotated_attribute` (:380-478).
**Signature:** `@staticmethod def from_annotated_attribute(annotation: type[Any], default: Any, *, _source: AnnotationSource = AnnotationSource.ANY) -> FieldInfo`.
**Data Shape:** `default` is one of: a plain value, a `FieldInfo` (from `Field()`), or a stdlib `dataclasses.Field`. Returns a fully constructed FieldInfo with `_qualifiers` set and `_final=True`.

### Decisive source
```python
if annotation is not MISSING and annotation is default:
    raise PydanticUserError(... code='unevaluable-type-annotation')   # name shadowing its own type
...
# HACK 1: the order in which the metadata is merged is inconsistent; we need to prepend
# metadata from the assignment at the beginning of the metadata.
prepend_metadata: list[Any] | None = None
attr_overrides = {'annotation': type_expr}
if final:
    attr_overrides['frozen'] = True

# HACK 2: FastAPI is subclassing `FieldInfo` ... expected the actual instance's type preserved
if not metadata and isinstance(default, FieldInfo) and type(default) is not FieldInfo:
    field_info = default._copy(); ...; return field_info

if isinstance(default, FieldInfo):
    default_copy = default._copy()  # Copy unnecessary when we remove HACK 1.
    prepend_metadata = default_copy.metadata
    default_copy.metadata = []
    metadata = metadata + [default_copy]
elif isinstance(default, dataclasses.Field):
    from_field = FieldInfo._from_dataclass_field(default)
    prepend_metadata = from_field.metadata
    from_field.metadata = []
    metadata = metadata + [from_field]
else:
    attr_overrides['default'] = default      # `default` is the actual default value

field_info = FieldInfo._construct(prepend_metadata + metadata if prepend_metadata is not None else metadata, **attr_overrides)
field_info._qualifiers = inspected_ann.qualifiers
field_info._final = True
```

**Flow:** guard against annotation-is-default name clash → `inspect_annotation` (qualifiers incl. `final`, metadata) → assignment FieldInfo/dataclass-Field metadata is MOVED to the FRONT of the Annotated metadata list (so later entries — i.e. Annotated's own — override earlier ones) → plain values become `attr_overrides['default']` → `_construct` merges everything; `final` forces `frozen=True`.
**Invariant:** The assigned `Field()`'s metadata is copied, never shared (`_copy()`), and ordering is stable: for `Annotated[int, AfterValidator(f1), Field(gt=1), AfterValidator(f2)] = Field(...)`, metadata stays `[AfterValidator(f1), Gt(1), AfterValidator(f2)]`. A reused module-level `Annotated[...]` alias must not be mutated by a second model using it.
**Probe:** `tests/test_fields.py::test_metadata_preserved_with_assignment` (:225-241) pins metadata order; `test_reused_field_not_mutated` (:244-255) pins copy-not-share across two models sharing one annotated alias; `test_final_to_frozen_with_assignment` (:216-222) pins final⇒frozen.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "collect_fields FieldInfo annotated attribute default factory", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt prepend-assignment-metadata merging with per-model copies and the final⇒frozen override. Adapt the two HACKs away only if your host has no FastAPI-style FieldInfo subclassers. Omit `AnnotationSource` gating details if you have no TypedDict/dataclass source split.
