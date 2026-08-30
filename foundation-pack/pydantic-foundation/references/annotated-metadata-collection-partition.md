<!-- capsule-v2 -->
# Annotated-metadata collection partition — how does pydantic split Annotated metadata into known constraints vs unknown remainder?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When an `Annotated[T, ...]` field reaches schema generation, which metadata items become constraint keys, which stay opaque, and what expansion quirks must a porter preserve?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_known_annotated_metadata.py:collect_known_metadata` (:344-386), `expand_grouped_metadata` :109-147, `_get_at_to_constraint_map` :149-170.
**Signature:** `collect_known_metadata(annotations: Iterable[Any]) -> tuple[dict[str, Any], list[Any]]`; `expand_grouped_metadata(annotations) -> Iterable[Any]`.
**Data Shape:** input is the raw `Annotated.__metadata__` tuple (or FieldInfo.metadata); output is a flat constraint dict (`{'gt': 1, 'min_length': 42}`) plus a remainder list of everything not recognized; docstring example: `collect_known_metadata([Gt(1), Len(42), ...])` → `({'gt': 1, 'min_length': 42}, [Ellipsis])`.

### Decisive source
```python
for annotation in annotations:
    # isinstance(annotation, PydanticMetadata) also covers ._fields:_PydanticGeneralMetadata
    if isinstance(annotation, PydanticMetadata):
        res.update(annotation.__dict__)
    elif (annotation_type := type(annotation)) in (at_to_constraint_map := _get_at_to_constraint_map()):
        constraint = at_to_constraint_map[annotation_type]
        res[constraint] = getattr(annotation, constraint)
    elif isinstance(annotation, type) and issubclass(annotation, PydanticMetadata):
        # also support PydanticMetadata classes being used without initialisation,
        # e.g. `Annotated[int, Strict]` as well as `Annotated[int, Strict()]`
        res.update({k: v for k, v in vars(annotation).items() if not k.startswith('_')})
    else:
        remaining.append(annotation)
# Nones can sneak in but pydantic-core will reject them
res = {k: v for k, v in res.items() if v is not None}
return res, remaining
```
and in `expand_grouped_metadata`, the FieldInfo arm yields `annotation.metadata` then a `copy(annotation)` with `annotation.metadata = []` — the source comment calls the resulting duplicate metadata "a bit problematic" but says all consumers handle it.

**Flow:** expand (GroupedMetadata flattened via iteration; FieldInfo exploded into inner metadata + cleared copy) → single pass classifies each item → known keys accumulate into one dict (later items overwrite earlier ones for the same key) → None-valued entries dropped at the end → remainder returned untouched.
**Invariant:** the partition is TOTAL and LOSSLESS — every input item ends up either in the dict or the remainder, never both and never dropped (except explicit Nones); the annotated_types map is built inside an `lru_cache`d function because module-level `import annotated_types` is forbidden to keep pydantic import fast; FieldInfo is copied before clearing so a shared `Field(...)` object used by several fields is never mutated.
**Probe:** `tests/test_annotated.py::test_annotated_allows_unknown` :115-123 (unknown metadata `0`/`'foo'` survives verbatim in `field_info.metadata` AND in the recorded `Annotated` type — i.e. it lands in the remainder, not the dict).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "collect_known_metadata expand_grouped_metadata PydanticMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-bucket partition with a lazily-built external-library map and the None-drop tail; adapt the class-form (`Annotated[int, Strict]`) support if your host forbids bare-class metadata; omit the FieldInfo-copy duplication only if your host never puts FieldInfo inside Annotated. Caveat: Retrieve written but not executed this pass (MCP unavailable); anchors verified by direct read at the pin.
