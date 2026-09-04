<!-- capsule-v2 -->
# lstr pydantic roundtrip schema — how does a str subclass survive pydantic serialization without losing its metadata?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I put provenance-carrying strings inside pydantic models (Message/ToolResult) so JSON round-trips preserve the metadata?

## Tagged-dict core schema
**Path/Symbol:** `src/ell/types/_lstr.py:_lstr.__get_pydantic_core_schema__` (:112-151).
**Signature:** classmethod `(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema`.
**Data Shape:** serialized form is `{"content": str, "__origin_trace__": "id1,id2", "__lstr": True}`; validator accepts an instance, a tagged dict, or a plain str.

### Decisive source
```python
return core_schema.json_or_python_schema(
    json_schema=core_schema.typed_dict_schema(
        {
            "content": core_schema.typed_dict_field(core_schema.str_schema()),
            "__origin_trace__": core_schema.typed_dict_field(
                core_schema.str_schema()
            ),
            "__lstr": core_schema.typed_dict_field(
                core_schema.bool_schema()
            ),
        }
    ),
    python_schema=core_schema.union_schema(
        [
            core_schema.is_instance_schema(cls),
            core_schema.no_info_plain_validator_function(validate_lstr),
        ]
    ),
    serialization=core_schema.plain_serializer_function_ser_schema(
        lambda instance: {
            "content": str(instance),
            "__origin_trace__": (instance.__origin_trace__),
            "__lstr": True,
        }
    ),
)
```

**Flow:** python-side validation short-circuits on `isinstance`; JSON-side validation rebuilds via `validate_lstr`, splitting the comma-joined trace string back into a list and re-wrapping. The `"__lstr": True` sentinel key discriminates tagged dicts from arbitrary user dicts.
**Invariant:** plain strings must coerce losslessly (`cls(value)`) — otherwise every legacy payload breaks; and the discriminator flag must round-trip or deserialization re-imports metadata-less strings. Note the asymmetry: serialization writes a frozenset into the dict while the JSON schema declares a string — downstream consumers join/split on commas.
**Probe:** `tests/test_lstr.py:test_init` pins construction semantics; end-to-end JSON behavior of containing models is pinned in `tests/test_message_type.py:test_message_json_serialization` (`model_dump_json` → `Message.model_validate_json` preserves role and content length).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "pydantic core schema lstr", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.types._lstr._lstr.__get_pydantic_core_schema__ @ src/ell/types/_lstr.py:113-151
```

## Verdict
Adopt the json-or-python + sentinel-tag pattern for any custom scalar needing metadata in pydantic v2. Adapt field names to your domain; keep dunder-style keys so they cannot collide with content keys. Omit the frozenset-vs-string asymmetry — normalize to a string at serialization time in your port.
