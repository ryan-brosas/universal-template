<!-- capsule-v2 -->
# gRPC host-side disconnect recovery — what happens to routes, subscriptions, and in-flight RPCs when a worker stream dies?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** Where must cleanup run when a bidi-stream client disappears, and what resilience actually exists for reconnects?

## Connection-finally cleanup ladder; reconnect is NOT implemented
**Path/Symbol:** `python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime_host_servicer.py` `OpenChannel` :114–140, `_on_client_disconnect` :165–178, `_wait_and_send_response` :255–264; worker side `_worker_runtime.py` `HostConnection._connect` read_loop :179–190, `_run_read_loop` :279–306, `DEFAULT_GRPC_CONFIG` retryPolicy :96–116.
**Signature:** `async def OpenChannel(self, request_iterator, context) -> AsyncIterator[Message]` · host tables: `_data_connections[client_id]`, `_pending_responses[client_id][request_id] -> Future`, `_agent_type_to_client_id[type]`, `_client_id_to_subscription_id_mapping[client_id]`.
**Data Shape:** per-client connection object wraps the request iterator with a send queue; disconnect = the `async for` over `OpenChannel`'s yielded iterator terminating.

### Decisive source
```python
try:
    async for message in connection:
        yield message
finally:
    # Clean up the client connection.
    del self._data_connections[client_id]
    # Cancel pending requests sent to this client.
    for future in self._pending_responses.pop(client_id, {}).values():
        future.cancel()
    # Remove the client id from the agent type to client id mapping.
    await self._on_client_disconnect(client_id)
```
```python
# _on_client_disconnect: drop every type this client owned and its subscriptions
async with self._agent_type_to_client_id_lock:
    agent_types = [t for t, id_ in self._agent_type_to_client_id.items() if id_ == client_id]
    for agent_type in agent_types:
        del self._agent_type_to_client_id[agent_type]
    for sub_id in self._client_id_to_subscription_id_mapping.get(client_id, set()):
        try:
            await self._subscription_manager.remove_subscription(sub_id)
        except ValueError:
            continue  # already gone — tolerated
```
```python
# worker side honesty: there is no reconnect, only channel-level retry of unary calls
# TODO: where do exceptions from reading the iterable go? How do we recover from those?   (:172)
# TODO: catch exceptions and reconnect                                                    (:282)
"retryableStatusCodes": ["UNAVAILABLE"]  # DEFAULT_GRPC_CONFIG service config, maxAttempts 3
```

**Flow:** stream ends (worker stop or socket death) → generator `finally`: delete connection → cancel ALL pending response futures for that client (unblocking `_wait_and_send_response` waiters) → under lock remove each type→client mapping → best-effort remove that client's subscriptions → a re-registering worker gets fresh ids and a clean routing table.
**Invariant:** cleanup is idempotent-by-tolerance (missing subscription ⇒ swallowed ValueError) and ownership-scoped (only the dead client's types/subscriptions are removed). The worker does NOT detect its own disconnection promptly: EOF just breaks the silent read-loop task, and in-flight `send_message` futures hang — porters must add their own liveness probe. The only automatic retry is gRPC's UNAVAILABLE retryPolicy on unary RPCs; the bidi stream itself is never re-established.
**Probe:** `python/packages/autogen-ext/tests/test_worker_runtime.py::test_disconnected_agent` (:398–459 — closing `worker1._host_connection` empties host subscriptions and recipients within ~2s, and worker1_2 then registers "worker1" successfully with NEW subscription ids).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "autogen", qualified_name: "autogen.python.packages.autogen-ext.src.autogen_ext.runtimes.grpc._worker_runtime_host_servicer.GrpcWorkerAgentRuntimeHostServicer.OpenChannel" });
```

## Verdict
Adopt the finally-block cleanup ladder scoped to the dead connection, including cancelling parked response futures so relayers unblock. Adapt ownership bookkeeping to your registry shape. Omit any assumption of worker-side reconnect — treat it as an explicit gap you must design (upstream left TODOs, and the flaky/skipped multi-worker cascade test corroborates that distributed failure modes were not hardened).
