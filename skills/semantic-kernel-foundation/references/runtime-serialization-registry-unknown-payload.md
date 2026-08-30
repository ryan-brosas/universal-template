<!-- capsule-v2 -->
# Runtime serialization registry — fail-open deserialize, fail-closed serialize, construction-time dataclass gates

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do runtime messages become bytes, and what happens when a payload arrives that no serializer claims?

## SerializationRegistry + UnknownPayload
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/serialization.py:SerializationRegistry` (lines 274–316), `UnknownPayload` (266–271), `DataclassJsonMessageSerializer.__init__` (147–165), `try_get_known_serializers_for_type` (252–264), `_type_name` (273–284 area).
**Signature:** `add_serializer(serializer | Sequence[MessageSerializer])`; `deserialize(payload, *, type_name, data_content_type) -> Any`; `serialize(message, *, type_name, data_content_type) -> bytes`; `try_get_known_serializers_for_type(cls) -> list[MessageSerializer]`.
**Data Shape:** Registry dict keyed `(type_name, data_content_type)`. `MessageSerializer` protocol = `data_content_type: str` + `type_name: str` + `serialize(message) -> bytes` + `deserialize(payload) -> T`. Three built-ins: `DataclassJsonMessageSerializer` (JSON, `asdict`/`cls(**json.loads)`), `PydanticJsonMessageSerializer` (JSON, `model_dump_json`/`model_validate_json`), `ProtobufMessageSerializer` (`google.protobuf.Any` Pack/Unpack, content type `application/x-protobuf`).

### Decisive source
```python
def deserialize(self, payload: bytes, *, type_name: str, data_content_type: str) -> Any:
    serializer = self._serializers.get((type_name, data_content_type))
    if serializer is None:
        return UnknownPayload(type_name, data_content_type, payload)
    return serializer.deserialize(payload)

def serialize(self, message: Any, *, type_name: str, data_content_type: str) -> bytes:
    serializer = self._serializers.get((type_name, data_content_type))
    if serializer is None:
        raise ValueError(f"Unknown type {type_name} with content type {data_content_type}")
    return serializer.serialize(message)

# DataclassJsonMessageSerializer.__init__ — construction-time gate:
if contains_a_union(cls):
    raise ValueError("Dataclass has a union type, which is not supported. To use a union, use a Pydantic model")
if has_nested_dataclass(cls) or has_nested_base_model(cls):
    raise ValueError("Dataclass has nested dataclasses or base models, ...")
```

**Flow:** `try_get_known_serializers_for_type` is an elif chain — pydantic BaseModel first, then dataclass, then protobuf `Message`; anything else returns `[]` (never raises). `add_serializer` accepts a sequence and recurses per item; the LAST write wins for a duplicate `(type_name, content_type)` key. `type_name` comes from `_type_name`: protobuf classes use `DESCRIPTOR.full_name`, plain classes use `__name__`. The asymmetry is the invariant: a deserialize miss means the wire carried something this process does not know, so the runtime wraps the raw bytes in `UnknownPayload(type_name, data_content_type, payload)` and keeps going; a serialize miss means the LOCAL code is wrong, so it raises. The dataclass serializer additionally fails closed AT CONSTRUCTION: union fields, nested dataclasses, and nested BaseModels are all rejected up front (via `contains_a_union`/`has_nested_dataclass`/`has_nested_base_model` using `is_union` from `type_helpers.py`) — pydantic is the designated escape hatch for any nested or unioned shape.
**Invariant:** Deserialize is fail-open (UnknownPayload), serialize is fail-closed (ValueError); dataclass serializers reject unions/nesting at construction, not at first use. A message type must be registered on BOTH sides of the wire or the receiving side silently degrades to UnknownPayload.
**Probe:** `python/tests/unit/agents/runtime/test_message_serialization.py::test_pydantic` (line 40 — exact wire bytes `b'{"message":"hello"}'`), `test_nesting_dataclass_dataclass` (line 84 — ValueError on nested dataclass), `test_nesting_union_old_syntax_dataclass` (line 100, parametrized — ValueError on union field), `test_custom_type` (line 117 — a hand-written protocol impl round-trips). CAVEAT recorded: `test_invalid_type` (line 108) is vacuous — `try_get_known_serializers_for_type(str)` returns `[]` without raising, so the `try/except ValueError` never asserts anything.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "SerializationRegistry UnknownPayload try_get_known_serializers_for_type DataclassJsonMessageSerializer", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the (type_name, data_content_type)-keyed registry with the fail-open/fail-closed asymmetry and construction-time dataclass gates for any actor-runtime wire format. Adapt: keep the UnknownPayload escape hatch but log it — this implementation drops it silently. Omit: the protobuf serializer if your transport never carries proto messages; the vacuous `test_invalid_type` pattern (assert the `[]` return instead).
