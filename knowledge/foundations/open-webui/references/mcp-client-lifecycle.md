<!-- capsule-v2 -->
# MCP client lifecycle — how do you host MCP client sessions whose SDK forbids shielded/cross-task teardown?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When a client SDK's transport owns an anyio TaskGroup that must be exited in the exact task that entered it, how do you connect with a bounded handshake, transfer cleanup ownership to the instance, and disconnect safely under cancellation — without `asyncio.shield`/`wait_for` turning teardown into a 500?

## Construction-time SSL + env-fallback timeout in the httpx factory
**Path/Symbol:** `backend/open_webui/utils/mcp/client.py:_build_httpx_client` (21-43) + `create_httpx_client` (46-52) / `create_insecure_httpx_client` (55-56).
**Signature:** `def _build_httpx_client(headers=None, timeout=None, auth=None, verify=True) -> httpx.AsyncClient`.
**Data Shape:** `verify` ∈ {True, False, ssl.SSLContext} from `AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL` (env.py:638); timeout falls back to `AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER`, which itself falls back to `AIOHTTP_CLIENT_TIMEOUT` when unset/unparseable (env.py:640-648).

### Decisive source
```python
Note: verify must be passed at construction time because httpx
configures the SSL context during __init__. Setting client.verify = False
after construction does not affect the underlying transport's SSL context.
```
(client.py 27-29)

**Flow:** the insecure factory is selected at CONNECT time by the SSL setting (`create_httpx_client if AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL else create_insecure_httpx_client`, :70-72), so the whole client is built with the right `verify`; an explicit caller timeout wins, else the tool-server env timeout, else nothing.
**Invariant:** TLS posture is a construction-time decision for httpx — a port that sets `client.verify = False` after the fact will still verify certificates and burn hours debugging "insecure mode" that never took effect.

## Connect: bounded handshake, ownership transfer via pop_all
**Path/Symbol:** `client.py:MCPClient.connect` (64-86).
**Signature:** `async def connect(self, url: str, headers: Optional[dict] = None)`; instance fields `session: Optional[ClientSession]`, `exit_stack`.
**Data Shape:** `MCP_INITIALIZE_TIMEOUT` default 10 s (env.py:653, parse-fail → 10).

### Decisive source
```python
self.session = await exit_stack.enter_async_context(self._session_context)
with anyio.fail_after(MCP_INITIALIZE_TIMEOUT):
    await self.session.initialize()
self.exit_stack = exit_stack.pop_all()
...
except Exception as e:
    await self.disconnect()
    raise e
```
(client.py 80-86)

**Flow:** build streamablehttp_client + ClientSession inside a LOCAL AsyncExitStack → enter both contexts → bound `initialize()` with `anyio.fail_after(MCP_INITIALIZE_TIMEOUT)` (the handshake is the one call that can hang on a dead server) → `pop_all()` transfers cleanup ownership from the stack to the instance so the connection outlives the `async with` block → ANY failure disconnects (which is safe pre-transfer because `disconnect()` tolerates a None stack) and re-raises.
**Invariant:** after a successful connect, exactly ONE owner exists for teardown (the instance's `exit_stack`); the local stack is empty, so no double-close path exists between connect and disconnect.

## Disconnect: null-before-close, no shield, cancellation-aware
**Path/Symbol:** `client.py:MCPClient.disconnect` (149-181).
**Signature:** `async def disconnect(self)` — idempotent; safe on a never-connected client.
**Data Shape:** suppresses RuntimeError/Exception at debug; re-raises CancelledError only when the current task is itself cancelling.

### Decisive source
```python
# Prevent double-close from concurrent callers
self.exit_stack = None
self.session = None

try:
    # IMPORTANT: Do NOT use asyncio.shield() or asyncio.wait_for()
    # because they create a new asyncio task, which violates the MCP SDK's
    # requirement that its TaskGroup be exited in the exact same task.
    # ALSO do NOT use anyio.CancelScope(shield=True) or anyio.fail_after(),
    # because they push a new cancel scope onto the task, violating LIFO
    # order when aclose() attempts to exit the inner TaskGroup.
    # We simply call aclose() directly. If the task is cancelled, the
    # sockets will eventually be cleaned up by garbage collection.
    await exit_stack.aclose()
except asyncio.CancelledError as exc:
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise
    log.debug('MCPClient.disconnect() suppressed internal cancellation: %s', exc)
```
(client.py 159-177, condensed)

**Flow:** capture the stack reference → NULL both fields BEFORE awaiting aclose (a concurrent second caller sees None and returns — the double-close guard) → plain `await exit_stack.aclose()` → CancelledError is re-raised only if `task.cancelling()` says the CURRENT task is genuinely cancelling (internal cancellations raised by the transport during its own shutdown are swallowed at debug).
**Invariant:** the SDK's TaskGroup must be exited in the same task with LIFO cancel-scope order — shield/wait_for spawn a new task, fail_after pushes a scope; both corrupt the exit sequence. A port that wraps this aclose in `asyncio.wait_for` will see "Attempted to exit a cancel scope that isn't the current task's current cancel scope" propagate as BaseException.

## Per-request lifecycle: fresh client per call, reversed-order finally cleanup
**Path/Symbol:** `backend/open_webui/utils/middleware.py:connect_mcp_server` (2197-2245) + `backend/open_webui/main.py` chat_completion finally block (1639-1646).
**Signature:** `async def connect_mcp_server(request, server_id, user, metadata, extra_params) -> tuple[MCPClient, list[dict]] | None`.
**Data Shape:** clients collected in `metadata['mcp_clients']` (middleware.py:2856-57); trace inbound `MCPClient.connect`: 3 callers (routers/configs.verify_tool_servers_config, middleware.connect_mcp_server, process_chat_payload hop-2).

### Decisive source
```python
# NOTE: asyncio.wait_for() / asyncio.shield() must NOT be used
# here — they create new asyncio Tasks, which violate anyio
# cancel-scope task-ownership rules when the MCPClient's
# exit_stack contains anyio transport resources (streamable_http).
# Exiting those cancel scopes from the wrong task raises
# "Attempted to exit a cancel scope that isn't the current
# task's current cancel scope", which propagates as a
# BaseException through the finally block, discards the response
# return value, and surfaces as a 500 "No response returned."
try:
    if mcp_clients := metadata.get('mcp_clients'):
        for client in reversed(list(mcp_clients.values())):
            try:
                await client.disconnect()
            except BaseException as e:
                log.debug(f'Error disconnecting MCP client: {e}')
```
(main.py 1627-1644, condensed)

**Flow:** each chat request that references `server:mcp:<id>` tool ids gets a FRESH MCPClient per server (no pooling), connects, lists tool specs, filters by `function_name_filter_list`; the resolved clients ride along in request metadata; the completion handler's finally block disconnects them in REVERSED insertion order, each in its own try/except so one failing teardown doesn't skip the rest.
**Invariant:** teardown order is LIFO over the connections (reversed dict order) and per-client failures are contained — a single dead transport must not leak its siblings' sockets or mask the response already being returned.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "exit_stack.pop_all()" backend/open_webui/utils/mcp/client.py` → 83; `grep -n "task.cancelling()" backend/open_webui/utils/mcp/client.py` → 175; `grep -n "anyio.fail_after(MCP_INITIALIZE_TIMEOUT)" backend/open_webui/utils/mcp/client.py` → 81; `grep -n "reversed(list(mcp_clients.values()))" backend/open_webui/main.py` → 1640.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "MCPClient connect disconnect exit_stack pop_all", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the construction-time verify factory, the pop_all ownership transfer, the null-before-close idempotent disconnect with `task.cancelling()` discrimination, and the per-request fresh-client + reversed-order contained-teardown lifecycle. Adapt the timeout/SSL env names and the metadata channel to your host. Omit open-webui's no-pooling choice only if you can prove your host keeps the same-task teardown guarantee across pooled reuse — the SDK constraint, not the product, is what forbids the shortcut. Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.
