<!-- capsule-v2 -->
# WS command envelope — request/response correlation, timeout ownership, and never-throw server routers

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should a WebSocket client correlate async commands to replies (with per-command timeouts), and how should the server route them so handler throws become typed error replies?

## requestId → pendingReplies map; timeout deletes-then-rejects; okReply/errorReply echo envelope
**Path/Symbol:** `sdk/packages/core/src/hub/client/index.ts:523-600` (`NodeHubClient.commandOnce`); `hub/server/handlers/context.ts:109-132` (`okReply`, `errorReply`); exemplar router `hub/server/handlers/connector-handlers.ts:256-300` (`handleConnectorCommand`).
**Signature:** `commandOnce(command, payload?, sessionId?, {timeoutMs? | null}) → Promise<HubReplyEnvelope>`; `okReply(envelope, payload?)`; `errorReply(envelope, code, message)`.
**Data Shape:** Request `{version:"v1", command, requestId:"hubreq_…", clientId, sessionId?, timeoutMs, payload?}`; reply `{version, requestId, ok:true, payload?} | {ok:false, error:{code,message}}`.

### Decisive source
```ts
const requestId = createSessionId("hubreq_");
const effectiveTimeoutMs = resolveHubCommandTimeoutMs(command, options?.timeoutMs); // null = opt out
... setTimeout(() => {
    if (!this.pendingReplies.delete(requestId)) return;   // late reply after timeout is dropped, not double-settled
    reject(new HubCommandError(command, "hub_command_timeout",
        `Hub command ${command} timed out ... (hub=${this.currentUrl}, requestId=${requestId}, clientId=${this.clientId}) ...`));
}, effectiveTimeoutMs);
this.pendingReplies.set(requestId, { resolve: ..., reject: ... });
try { this.sendFrame({ kind: "command", envelope: {...} }); }
catch (error) { this.pendingReplies.delete(requestId); throw error; }   // send failure cleans up
if (!resolved.ok) {
    if (resolved.error?.code === SESSION_NOT_FOUND_ERROR_CODE)
        throw new SessionNotFoundError(targetSessionId, resolved.error.message);   // code => typed error mapping
    throw new HubCommandError(command, resolved.error?.code, ...);
}

// SERVER side: pure constructors echoing version+requestId back
return { version: envelope.version, requestId: envelope.requestId, ok: true, ...(payload !== undefined ? { payload } : {}) };
// Router converts every throw into a reply — handlers never reject the socket:
catch (error) { captureConnectorCommandUsage(ctx, envelope, false);
    return errorReply(envelope, "connector_command_failed", error instanceof Error ? error.message : String(error)); }
```

**Flow:** client registers pending callback under requestId before sending; send-frame failure removes it; timeout path deletes first so a late reply cannot resolve after rejection; transport close rejects ALL pending replies with `lastCloseError` and clears the map. Replies map known codes to typed errors (`session_not_found` ⇒ `SessionNotFoundError`). Server routers dispatch on `envelope.command`, wrap each arm in try/catch, emit usage telemetry on success AND failure, and answer unknown commands with a stable `unsupported_connector_command` code.
**Invariant:** Every request settles exactly once; every server-side throw becomes an error reply on the same socket (routers never rethrow into the transport); timeouts are per-command overridable with explicit null opt-out; diagnostic errors carry hub url + requestId + clientId.
**Probe:** `grep -cF 'this.pendingReplies.set(requestId, {' sdk/packages/core/src/hub/client/index.ts` → 1; `grep -cF 'error: { code, message },' sdk/packages/core/src/hub/server/handlers/context.ts` → 1; `grep -cF '"unsupported_connector_command",' sdk/packages/core/src/hub/server/handlers/connector-handlers.ts` → 1. Direct tests: `client/index.test.ts` ("times out when a hub command never replies", "allows commands to opt out of the reply timeout", "rediscovers the local hub and retries commands after transport close").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "commandOnce pendingReplies okReply errorReply HubCommandEnvelope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delete-before-reject timeout idempotence, cleanup-on-send-failure, close-rejects-all-pending, and catch-everything routers with stable unknown-command codes. Adapt envelope fields, code vocabulary, telemetry. Omit Cline's session/host specifics. Runner-BLOCKED here; probes green.
