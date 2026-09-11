<!-- capsule-v2 -->
# gRPC registration handshake — how does a worker claim agent types on a host without colliding with other workers?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** In what order must a worker register factories and subscriptions against a shared host, and what happens when two workers claim the same type?

## Local-factory-first, host-RPC-second; host owns the type→client map
**Path/Symbol:** `python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime.py` `register_factory` :713–744, `_register_agent_type` :705–711, `add_subscription` :822–832; `python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime_host_servicer.py` `RegisterAgent` :287–306, `AddSubscription` :308–324.
**Signature:** `async def register_factory(self, type: str | AgentType, agent_factory: Callable[[], T | Awaitable[T]], *, expected_class: type[T] | None = None) -> AgentType` · `async def RegisterAgent(self, request: RegisterAgentTypeRequest, context: ServicerContext) -> RegisterAgentTypeResponse`.
**Data Shape:** worker keeps `_agent_factories: Dict[str, factory_wrapper]`; host keeps `_agent_type_to_client_id: Dict[str, ClientConnectionId]` guarded by one asyncio.Lock; every RPC carries `("client-id", uuid4)` metadata (`HostConnection.metadata` :130–132), enforced by `get_client_id_or_abort` (aborts INVALID_ARGUMENT if missing).

### Decisive source
```python
# worker: local registry first, then the host unary call
if type.type in self._agent_factories:
    raise ValueError(f"Agent with type {type} already exists.")
...
self._agent_factories[type.type] = factory_wrapper
# Send the registration request message to the host.
await self._register_agent_type(type.type)
```
```python
# host: duplicate claim aborts the RPC under the lock
async with self._agent_type_to_client_id_lock:
    if request.type in self._agent_type_to_client_id:
        existing_client_id = self._agent_type_to_client_id[request.type]
        await context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            f"Agent type {request.type} already registered with client {existing_client_id}.",
        )
    else:
        self._agent_type_to_client_id[request.type] = client_id
```
```python
# subscriptions: host accepted first, then mirrored into the LOCAL manager
_response = await self._host_connection.stub.AddSubscription(message, metadata=self._host_connection.metadata)
await self._subscription_manager.add_subscription(subscription)
```

**Flow:** `start()` must run first (registration needs `_host_connection`) → `register_factory`: dup-check locally → wrap factory (awaitable-tolerant, `expected_class` checked at instantiation) → store → unary `RegisterAgent` → `add_subscription`: proto-convert via `subscription_to_proto` → host `AddSubscription` (dup id ⇒ INVALID_ARGUMENT) → mirror locally.
**Invariant:** the host's type→client mapping is single-writer under one lock and is the routing authority for all later RPC/event delivery; a duplicate type claim is a hard abort, not a warning — so the same type name can live on exactly one worker at a time. Registration order matters: host-first for subscriptions means a subscription never exists locally while the host rejected it.
**Probe:** `python/packages/autogen-ext/tests/test_worker_runtime.py::test_agent_types_must_be_unique_multiple_workers` (:63–84 — worker2 registering "name1" raises `Exception, match="Agent type name1 already registered"`) and `test_duplicate_subscription` (:366–393 — after worker1 stops, re-register succeeds because disconnect released the type).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", qn_pattern: "^autogen\\.python\\.packages\\.autogen-ext\\.src\\.autogen_ext\\.runtimes\\.grpc\\._worker_runtime_host_servicer\\.GrpcWorkerAgentRuntimeHostServicer\\.", limit: 25 });
```

## Verdict
Adopt the two-sided registry shape: workers own instantiation, the hub owns routing identity, and claims are exclusive-with-abort. Adapt client-id metadata to your transport's auth/identity headers and the protobuf registration messages to your wire format. Omit the deprecated two-argument factory path (warns and will be removed upstream).
