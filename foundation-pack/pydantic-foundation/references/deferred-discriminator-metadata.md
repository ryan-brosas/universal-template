<!-- capsule-v2 -->
# Deferred discriminator application via metadata — why is `set_discriminator_in_metadata` a two-phase handshake?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** How does a discriminator requested during generation get applied AFTER the full schema (with definitions) exists?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_discriminated_union.py:set_discriminator_in_metadata` (:28-30) + `pydantic/_internal/_schema_gather.py:traverse_metadata` (:90-93) and `GatherResult.deferred_discriminator_schemas` (:29-30).
**Signature:** `def set_discriminator_in_metadata(schema: CoreSchema, discriminator: Any) -> None` — sets `schema['metadata']['pydantic_internal_union_discriminator']`.
**Data Shape:** Core metadata dict doubles as the message channel; gather phase returns `deferred_discriminator_schemas: list[CoreSchema]`.

### Decisive source
```python
# phase 1 — during schema generation, when definitions aren't known yet:
def set_discriminator_in_metadata(schema, discriminator):
    metadata = cast('CoreMetadata', schema.setdefault('metadata', {}))
    metadata['pydantic_internal_union_discriminator'] = discriminator

# phase 2 — during cleaning, collect every union carrying the marker:
def traverse_metadata(schema: AllSchemas, ctx: GatherContext) -> None:
    meta = schema.get('metadata')
    if meta is not None and 'pydantic_internal_union_discriminator' in meta:
        ctx.deferred_discriminator_schemas.append(schema)

# consumer (GenerateSchema.clean_schema) then calls apply_discriminator(union, marker, definitions)
```

**Flow:** `Field(discriminator=...)` during annotation→schema conversion can't see global definitions yet ⇒ stash the discriminator in core metadata on the union schema → after the whole model graph exists, the clean/gather pass walks every schema and harvests marked unions → each is converted via `apply_discriminator(schema, marker, definitions)` where ref resolution CAN succeed (`MissingDefinitionForUnionRef` otherwise).
**Invariant:** The metadata key is namespaced `pydantic_internal_*` — internal markers must be stripped/ignored by JSON-schema emission; the marker travels WITH the schema object through caching, so deferred application survives schema reuse across models.
**Probe:** `grep -n 'pydantic_internal_union_discriminator' pydantic/_internal/_discriminated_union.py pydantic/_internal/_schema_gather.py` (producer + consumer pair).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "deferred discriminator metadata union", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase mark-then-apply pattern for any post-processing that needs whole-graph context; adapt key naming; omit JSON-schema interplay.
