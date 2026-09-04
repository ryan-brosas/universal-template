<!-- capsule-v2 -->
# Single-annotation schema-shape branches — how does one Annotated metadata item reach the right schema node?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** Before any constraint is applied, how does pydantic route a single metadata item through nullable wrappers, MISSING-sentinel unions, and ref'd definitions — and when is the original schema returned untouched?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generate_schema.py:GenerateSchema._apply_single_annotation` (:2291-2405).
**Signature:** `_apply_single_annotation(self, schema: CoreSchema, metadata: Any, check_unsupported_field_info_attributes: bool = True) -> CoreSchema`.
**Data Shape:** one core schema (any shape) + one already-expanded metadata item; returns a possibly-new schema; `None` from the downstream `apply_known_metadata` means "return the ORIGINAL object".

### Decisive source
```python
if isinstance(metadata, FieldInfo):
    ...  # unsupported-attribute warnings only when type(metadata) is FieldInfo (FastAPI-subclass hack)
    for field_metadata in metadata.metadata:
        schema = self._apply_single_annotation(schema, field_metadata)
    if metadata.discriminator is not None:
        schema = self._apply_discriminator_to_union(schema, metadata.discriminator)
    return schema

if schema['type'] == 'nullable':
    inner = schema.get('schema', core_schema.any_schema())
    inner = self._apply_single_annotation(inner, metadata)   # recurse into the non-null branch
    ...
if schema['type'] == 'union' and any(choice['type'] == 'missing-sentinel' for choice in core_schema.iter_union_choices(schema)):
    filtered_choices = [choice for choice in schema['choices'] if ...['type'] != 'missing-sentinel']
    if len(filtered_choices) >= 2:      # Annotated[int | str | MISSING, Constraint(...)] → constrain int|str, keep sentinel
        ...
    elif len(filtered_choices) == 1:    # Annotated[int | MISSING, Constraint(...)] → constrain int, rebuild union in order
        ...
ref = schema.get('ref')
if ref is not None:
    schema = schema.copy()
    new_ref = ref + f'_{repr(metadata)}'
    if (existing := self.defs.get_schema_from_ref(new_ref)) is not None:
        return existing                 # identical annotation on the same def → shared clone
    schema['ref'] = new_ref
elif schema['type'] == 'definition-ref':
    ... resolve referenced schema, copy it, same suffix rule ...

maybe_updated_schema = _known_annotated_metadata.apply_known_metadata(metadata, schema)
if maybe_updated_schema is not None:
    return maybe_updated_schema
return original_schema                  # unknown metadata → the very same object, unmodified
```

**Flow:** FieldInfo recurses into its own `.metadata` list then applies its discriminator and returns early → nullable schemas push the metadata into their inner schema → unions containing a `missing-sentinel` choice filter the sentinel out, apply to the surviving sub-union (≥2 choices) or the single survivor (==1), then rebuild the union preserving choice order → schemas carrying a `ref` are cloned under `ref + '_' + repr(metadata)` with a defs-cache lookup so two fields annotated identically share ONE def; bare `definition-ref`s first resolve to the referenced schema before the same clone rule applies → finally `apply_known_metadata` runs, and its None result returns the original schema object unchanged.
**Invariant:** unknown metadata must leave the schema byte-identical (the function returns the SAME object, not a copy); the missing-sentinel filtering never drops the sentinel — it only constrains the non-sentinel side; ref-cloning keys on `repr(metadata)`, so metadata objects with stable `__repr__` are what make the dedup work; the FastAPI-subclass identity check (`type(metadata) is FieldInfo`) gates the unsupported-attribute warning so subclassed FieldInfos stay quiet.
**Probe:** `tests/test_missing_sentinel.py::test_missing_sentinel_constraints_pushdown` :109-125 (`Annotated[int | MISSING, Ge(1)]` yields JSON `{'minimum': 1, 'type': 'integer'}` — the constraint pushed through the sentinel choice; f3/f4 show the ≥2-choice filtered-union shape); `tests/test_annotated.py::test_annotated_allows_unknown` :115-123 pins the untouched-original path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "_apply_single_annotation missing-sentinel nullable definition-ref", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape-dispatch-before-constraint order (FieldInfo → nullable → sentinel-union → ref-clone → known-metadata → original fallback) and the repr-keyed def dedup; adapt the sentinel concept to your host's optional-missing representation; omit the FastAPI identity hack unless your host has FieldInfo subclasses. Caveat: no direct test found for the ref-cloning branch at this pin (grep for refs assertions came up empty) — mechanics stated from source only. Retrieve written but not executed this pass (MCP unavailable).
