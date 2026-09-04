<!-- capsule-v2 -->
# Runtime serialization consumers — @handles fail-loud registration and observability-only _try_serialize

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Where do registered message serializers actually meet the message path, and what happens to a message type nobody registered?

## Consumer side of the serialization registry
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/base_agent.py:handles` (52–67), `BaseAgent.__init_subclass__` (81–88), `BaseAgent.register` (181–221, serializer loop 216–219); `python/semantic_kernel/agents/runtime/in_process/in_process_runtime.py:_try_serialize` (847–854), `add_message_serializer` (843–845), event-log call sites (228, 291, 359, 389, 400, 409, 448, 478, 509, 570, 610, 636).
**Signature:** `@handles(msg_type, serializer: MessageSerializer | list | None = None)`; `runtime.add_message_serializer(serializer | Sequence)`; `_try_serialize(message: Any) -> str`.
**Data Shape:** `internal_extra_handles_types: ClassVar[list[tuple[type, list[MessageSerializer]]]]` (re-created per subclass by `__init_subclass__`); registry keyed `(type_name, data_content_type)`; in-process envelopes carry LIVE OBJECTS — `payload: str` exists only on event-log records (MessageEvent / MessageDroppedEvent).

### Decisive source
```python
def handles(msg_type, serializer=None):
    def decorator(cls):
        if serializer is None:
            serializer_list = try_get_known_serializers_for_type(msg_type)
        else:
            serializer_list = [serializer] if not isinstance(serializer, Sequence) else list(serializer)
        if not serializer_list:
            raise ValueError(f"No serializers found for type {msg_type!r}. Please provide an explicit serializer.")
        cls.internal_extra_handles_types.append((msg_type, serializer_list))
        return cls
    return decorator

# in_process_runtime.py — the ONLY consumer of the registry on the hot path:
def _try_serialize(self, message: Any) -> str:
    try:
        type_name = self._serialization_registry.type_name(message)
        return self._serialization_registry.serialize(
            message, type_name=type_name, data_content_type=JSON_DATA_CONTENT_TYPE
        ).decode("utf-8")
    except ValueError:
        return "Message could not be serialized"
```

**Flow:** `@handles` resolves serializers AT DECORATION TIME and fails LOUD (ValueError) when the pydantic→dataclass→protobuf elif chain yields nothing — the fail-loud twin of the registry's fail-open deserialize (runtime-serialization-registry-unknown-payload capsule). `__init_subclass__` re-initializes both ClassVar lists per subclass, so decorator registrations never leak across sibling agent classes. `BaseAgent.register` walks `_handles_types()` and calls `runtime.add_message_serializer(serializer)` per pair — duplicate registration is currently allowed (TODO(evmattso): deduplication) but harmless because the registry's last-write-wins makes re-adding a no-op in effect. THE CRITICAL FINDING: `_try_serialize` is called ONLY to build event-log payloads (MessageEvent at send/publish/process/ack sites, MessageDroppedEvent in the intervention arms) — the in-process envelopes carry the live message object and the registry is never consulted for delivery. An unregistered message type therefore degrades only OBSERVABILITY: `_try_serialize` swallows the registry's serialize ValueError and returns the literal string "Message could not be serialized" into the event log, while the message itself flows untouched. `type_name` is derived per message via `registry.type_name(message)`; content type is pinned to JSON_DATA_CONTENT_TYPE. Tests pin the manual-registration pattern: both publish tests call `runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))` BEFORE register_factory because the test agents do not use `@handles`.
**Invariant:** Registration is fail-loud at decoration time; consumption is fail-soft at event-log time; delivery never serializes in-process. A missing serializer can never break message flow — only the event log's fidelity.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py:179` and `:209` — both `runtime.add_message_serializer(try_get_known_serializers_for_type(MessageType))` manual-registration lines (byte-verified by direct read). Coverage gap recorded: `@handles` and `subscription_factory` have ZERO test coverage at this pin (grep across python/tests = 0 hits) — the decorator contract rests on source reading alone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "handles try_get_known_serializers_for_type add_message_serializer _try_serialize MessageEvent internal_extra_handles_types", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: fail-loud serializer resolution at registration plus fail-soft observability-only serialization for any actor runtime that passes live objects in-process. Adapt: keep a real transport (gRPC/queue) serializing for delivery — then the fail-open deserialize path becomes load-bearing and the event-log degradation string should become a metric. Omit: the `@handles` decorator entirely if your runtime never logs payloads; register serializers directly.
