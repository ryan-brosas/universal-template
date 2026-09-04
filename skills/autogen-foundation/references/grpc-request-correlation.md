<!-- capsule-v2 -->
# gRPC request correlation — how does an RPC round trip over a message stream keep its result and its errors straight?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** How do you correlate a response arriving on a shared bidi stream with the awaiting caller, and what does an agent-side exception look like when it crosses the wire?

## Monotonic request_id + future table; errors travel as strings
**Path/Symbol:** `python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime.py` `send_message` :366–411, `_get_new_request_id` :507–510, `_process_response` :584–603; handler side `_process_request` :512–582.
**Signature:** `async def send_message(self, message: Any, recipient: AgentId, *, sender: AgentId | None = None, cancellation_token: CancellationToken | None = None, message_id: str | None = None) -> Any` · `async def _get_new_request_id(self) -> str`.
**Data Shape:** `_pending_requests: Dict[str, Future[Any]]` keyed by stringified monotonic counter (incremented under `asyncio.Lock`); wire envelope is protobuf oneof `Message{request: RpcRequest, response: RpcResponse, cloudEvent}`; `RpcRequest{request_id, target AgentId, source AgentId?, metadata, payload{data_type, data, data_content_type}}`.

### Decisive source
```python
# caller side: park the future BEFORE the bytes leave
future = asyncio.get_event_loop().create_future()
request_id = await self._get_new_request_id()
self._pending_requests[request_id] = future
...
task = asyncio.create_task(self._send_message(runtime_message, "send", recipient, telemetry_metadata))
self._background_tasks.add(task)
task.add_done_callback(self._raise_on_exception)
return await future
```
```python
# reply side: pop and resolve — error string becomes a GENERIC Exception
future = self._pending_requests.pop(response.request_id)
if len(response.error) > 0:
    future.set_exception(Exception(response.error))
else:
    future.set_result(result)
```
```python
# handler side: ANY BaseException is flattened to str(e) on the wire
except BaseException as e:
    response_message = agent_worker_pb2.Message(
        response=agent_worker_pb2.RpcResponse(request_id=request.request_id, error=str(e), ...))
    await self._host_connection.send(response_message)
    return
```

**Flow:** serialize → mint id → park future → background-task the enqueue → await future · host relays request to target worker's stream → target worker deserializes, builds `MessageContext(is_rpc=True)` with a FRESH CancellationToken per delivery, runs the agent under `MessageHandlerContext.populate_context` → success re-serializes result; failure sends `error=str(e)` → original worker's read loop dispatches `_process_response` which pops and resolves.
**Invariant:** every request parks exactly one future under exactly one id before any await on the wire; resolution always pops first, so a late/duplicate response surfaces as KeyError in a background task rather than corrupting another call. Exception TYPE fidelity is deliberately lost across the wire — only the string survives; porters needing typed errors must encode them into the payload themselves.
**Probe:** `python/packages/autogen-ext/tests/test_worker_runtime.py::test_instance_factory_messaging` (:654–685 — `send_message` returns the loopback result as an equal `ContentMessage`, proving the full serialize→route→run→serialize→resolve round trip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "autogen", qualified_name: "autogen.python.packages.autogen-ext.src.autogen_ext.runtimes.grpc._worker_runtime.GrpcWorkerAgentRuntime._process_response" });
```

## Verdict
Adopt id-keyed future tables parked before enqueue for any multiplexed request/response transport. Adapt the protobuf oneof envelope and telemetry-metadata plumbing to your wire. Omit the stringly-typed error channel if your host can afford a structured error payload — upstream chose minimalism here knowingly.
