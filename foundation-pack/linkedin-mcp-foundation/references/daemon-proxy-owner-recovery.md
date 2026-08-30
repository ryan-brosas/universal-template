<!-- capsule-v2 -->
# Daemon proxy owner recovery — forwarding that survives the owner it was built against

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** When the shared owner a proxy forwards to dies or is stood down mid-call, how does the frontend recover without replaying a mutating request?

## DaemonProxyBackend + FrontendOwnerRecoveryMiddleware
**Path/Symbol:** `linkedin_mcp_server/daemon_proxy.py` — `DaemonProxyBackend.open_client` (:505-561), `recover`/:​`_elect` (:433-503), `OwnerUnreachableError` (:138-205), ``_the_owner_answered'' (:214-283), `create_proxy_provider` (:564-588), `FrontendOwnerRecoveryMiddleware` (:591-690).
**Signature:** `open_client(*, timeout: float) -> ProxyClient`; `recover(failed_instance: str) -> Attachment | None`; `OwnerUnreachableError(*, instance_id: str, nothing_was_sent: bool, cause)`.
**Data Shape:** Address+token read PER operation from the current attachment (never captured); failure carries which owner failed and whether the request left this process.

### Decisive source
```python
# :458-469 — identity check first; one shielded election in flight
if self._attachment.descriptor.instance_id != failed_instance:
    return self._attachment          # somebody already replaced it
electing = self._electing
if electing is None:
    electing = asyncio.create_task(self._elect(failed_instance))
    self._electing = electing
return await asyncio.shield(electing)

# :675-690 — the whole replay rule
if not failure.nothing_was_sent and await a_repeat_could_change_something(context):
    logger.info("Attached to a replacement owner; not repeating a call that "
                "could change something")
    raise                              # the user knows; this process cannot
logger.info("Attached to a replacement owner; running the call again")
return await call_next(context)
```
**Flow:** call fails → walk cause chain for `OwnerUnreachableError` → recover for the NEXT call even if this one can't repeat → repeat ONLY when nothing was sent (`ConnectError`/`ConnectTimeout`) or the tool's `readOnlyHint` says safe → listings always repeat (they change nothing). Departure signals: client-invented McpError codes CONNECTION_CLOSED / REQUEST_TIMEOUT / 32600 "Session terminated".
**Invariant:** No cached session/address/token — a factory reading current state is what follows a replacement owner. The frontend deadline is owner tool_timeout + margin so the OWNER reports "tool timed out"; it does not bound queued calls. Component cache stays at TTL 0: clear-on-adoption is unsound because ProxyProvider writes caches after a listing completes, outside any lock. Elections run in a thread (`obtain_owner` probes via asyncio.run) and are shielded from callers' deadlines.
**Probe:** `tests/test_daemon_proxy.py` — `TestRepeatingOnlyWhatIsSafe` (:722-790) drives the middleware with `nothing_was_sent` × readOnly matrices; `TestTheForwardingDeadline` (:297-340) pins deadline == 72 s for tool_timeout 42 and MCP-layer (not only HTTP) placement.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "DaemonProxyBackend recover FrontendOwnerRecoveryMiddleware OwnerUnreachableError", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-operation factories, boundary-classified failures carrying identity + nothing-was-sent, single-flight shielded recovery, and annotation-driven replay safety for ANY proxy-over-loopback tool server whose backend can be replaced underneath it. Adapt deadline margins to your owner's timeout model. Omit FastMCP ProxyProvider internals unless you use fastmcp. Caveat: departure-code matching is convention (this owner never raises McpError itself), documented in-source — keep that assumption with the port.
