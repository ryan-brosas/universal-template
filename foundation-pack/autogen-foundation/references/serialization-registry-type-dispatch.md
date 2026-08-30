<!-- capsule-v2 -->
# Serialization registry — how do messages cross a wire without a shared type system, and what happens to unknown types?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** How is message (de)serialization dispatched by type name, and why do deserialize and serialize fail differently on unknown types?

## Tuple-keyed registry; UnknownPayload on deserialize-miss, ValueError on serialize-miss
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_serialization.py` (`MessageSerializer` protocol :14–23, `UnknownPayload` :187–191, `_type_name` :194–205, `try_get_known_serializers_for_type` :211–222, `SerializationRegistry` :225–258); populated via `SingleThreadedAgentRuntime.add_message_serializer` :1019–1020 and consumed at grpc wire ingress (`GrpcWorkerAgentRuntime._process_event/_process_request/_process_response`).
**Signature:** `def deserialize(self, payload: bytes, *, type_name: str, data_content_type: str) -> Any` / `def serialize(self, message: Any, *, type_name: str, data_content_type: str) -> bytes` / `def try_get_known_serializers_for_type(cls) -> list[MessageSerializer[Any]]`.
**Data Shape:** one dict `(type_name, data_content_type) -> MessageSerializer`; `UnknownPayload{type_name, data_content_type, payload}` is a plain dataclass RETURNED AS A VALUE on deserialize misses. Type names follow two regimes: protobuf ⇒ `DESCRIPTOR.full_name` ("agents.ProtoMessage"), everything else ⇒ BARE class name ("PydanticMessage").

### Decisive source
```python
# _type_name: two naming regimes; bare names collide across modules
if isinstance(cls, type):
    if issubclass(cls, Message):
        return cast(str, cls.DESCRIPTOR.full_name)
...
if isinstance(cls, type):
    return cls.__name__

# registry lookup arms are asymmetric:
def deserialize(self, payload, *, type_name, data_content_type):
    serializer = self._serializers.get((type_name, data_content_type))
    if serializer is None:
        return UnknownPayload(type_name, data_content_type, payload)   # VALUE, never raises
    return serializer.deserialize(payload)

def serialize(self, message, *, type_name, data_content_type):
    serializer = self._serializers.get((type_name, data_content_type))
    if serializer is None:
        raise ValueError(f"Unknown type {type_name} with content type {data_content_type}")
```

**Flow:** declare a message type → `try_get_known_serializers_for_type` picks ONE serializer by an if/elif ladder (pydantic BaseModel → dataclass → protobuf; anything else ⇒ empty list) → caller registers via `runtime.add_message_serializer(...)` (accepts single or Sequence, recursing) → at wire ingress grpc calls `deserialize(payload, type_name=..., data_content_type=...)`; a miss yields `UnknownPayload` which flows onward like any message → egress `serialize` raises loudly on a miss.
**Invariant:** deserialize NEVER raises for unknown types — callers MUST isinstance-check for `UnknownPayload`; serialize fails loud. Bare-name typing means two same-named classes in different modules share one registry key (collision hazard — prefix your names or use protobuf full names). Dataclass serializers reject union fields and nested dataclass/BaseModel fields at construction (:102–110): nesting support is pydantic-only. `test_invalid_type` (:137–142) is VACUOUS: `try_get_known_serializers_for_type(str)` returns `[]`, `add_serializer` iterates zero items, so its asserted ValueError can never fire.
**Probe:** `python/packages/autogen-core/tests/test_serialization.py::test_proto` (:89–98 pins `"agents.ProtoMessage"` vs `::test_pydantic` :46–56 pinning bare `"PydanticMessage"`) and `::test_custom_type` (:145–169 — a hand-written `MessageSerializer[str]` round-trips through the same registry).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "SerializationRegistry MessageSerializer serialize deserialize type_name", file_pattern: "_serialization.py", limit: 20 });
```

## Verdict
Adopt the tuple-keyed registry with value-typed unknown-payload deserialization for any plugin-extensible wire format — it lets heterogeneous workers interoperate without shared schemas. Adapt the naming regime to fully-qualified names if your host has namespace collisions. Omit the dataclass JSON path entirely (use pydantic) unless you need zero-dependency messages.
