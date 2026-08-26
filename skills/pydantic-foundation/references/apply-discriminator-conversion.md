<!-- capsule-v2 -->
# `apply_discriminator` union→tagged-union conversion — how is a plain union rewritten into a tagged union at schema level?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** How are discriminator values inferred from each choice, and which wrapper schemas must be unwrapped/preserved along the way?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_discriminated_union.py:apply_discriminator` (:33-69) + `_ApplyInferredDiscriminator._apply_to_root` (:169-234).
**Signature:** `def apply_discriminator(schema: CoreSchema, discriminator: str | Discriminator, definitions: dict[str, CoreSchema] | None = None) -> CoreSchema`.
**Data Shape:** Stateful walker: `_choices_to_handle: list[CoreSchema]` (stack), `_tagged_union_choices: dict[Any, CoreSchema]`, flags `_should_be_nullable`, `_is_nullable`, `_discriminator_alias`, one-shot `_used`.

### Decisive source
```python
def _apply_to_root(self, schema):
    if schema['type'] == 'nullable':
        self._is_nullable = True
        wrapped = self._apply_to_root(schema['schema'])
        nullable_wrapper = schema.copy(); nullable_wrapper['schema'] = wrapped; return nullable_wrapper
    if schema['type'] == 'definitions':
        ... unwrap and preserve ...
    if schema['type'] == 'definition-ref':
        def_schema = self.definitions[schema_ref]
        if def_schema['type'] == 'union':          # type alias to a referenceable union
            schema = def_schema.copy(); schema.pop('ref')
    if schema['type'] != 'union':
        # single-member union (pydantic-core flattened it) — still allow, for tagged error messages:
        schema = core_schema.union_schema([schema])
    choices_schemas = [v[0] if isinstance(v, tuple) else v for v in schema['choices'][::-1]]
    self._choices_to_handle.extend(choices_schemas)
    while self._choices_to_handle:
        self._handle_choice(self._choices_to_handle.pop())
    ...
    discriminator = [[self.discriminator], [self._discriminator_alias]] if alias-differs else self.discriminator
    return core_schema.tagged_union_schema(choices=self._tagged_union_choices, discriminator=discriminator,
                                           custom_error_type=schema.get('custom_error_type'), strict=False,
                                           from_attributes=True, ref=schema.get('ref'), ...)
```

**Flow:** unwrap `nullable`/`definitions`/ref-to-union wrappers (REBUILDING them around the result) → coerce non-unions into single-choice unions → push choices REVERSED so the stack pops in declaration order → per choice: coalesce nested unions and same-discriminator tagged-unions (`_is_discriminator_shared`), track None choices as nullability, else infer literal values → build final `tagged_union_schema`, re-wrapping in `nullable_schema` if a None choice was seen but no outer nullable survived.
**Invariant:** Discriminator values come ONLY from Literal fields (`_infer_discriminator_values_for_inner_schema` accepts literal/none/union-of-literals/default-wrapped/function-after-wrapped/RootModel[Literal]; anything else ⇒ `discriminator-needs-literal`; function-before/wrap/plain validators on the field ⇒ `discriminator-validator`). Duplicate value→choice mappings are legal only when they resolve to the SAME choice (`_set_unique_choice_for_values` walks existing entries). All choices must share ONE alias (`discriminator-alias`); the python name is the discriminator, never the alias.
**Probe:** `grep -n '_should_be_nullable and not self._is_nullable' pydantic/_internal/_discriminated_union.py` (:164 — the re-wrap condition).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "apply_discriminator tagged union choices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the infer-and-coalesce algorithm with its stack discipline and nullable bookkeeping; adapt the error taxonomy codes; omit pydantic-core `TaggedUnionValidator` runtime details (fallback chain lives in Rust).
