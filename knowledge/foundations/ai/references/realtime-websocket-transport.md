<!-- capsule-v2 -->
# Realtime WebSocket transport — how are sends ordered, stale sockets discarded, and health checks answered?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does `BrowserRealtimeTransport` guarantee send ordering under async serialization and correct lifecycle when sockets overlap?

## Send-queue chaining + immediate socket tracking
**Path/Symbol:** `packages/ai/src/realtime/browser-realtime-transport.ts` — `sendEvent` promise-chain (:78–93), `connect` tracking guards (:30–71), `handleMessage` health-check hook (:114–142).
**Signature:** `sendEvent(event: RealtimeClientEvent): void` — chains onto `sendQueue: Promise<void>`; `connect({token, url, onOpen}): void`.
**Data Shape:** serialized client events may be string/ArrayBuffer/TypedArray/Blob (sent RAW) or objects (JSON.stringify); server messages may arrive as string/Blob/ArrayBuffer.

### Decisive source
```ts
this.sendQueue = this.sendQueue
  .then(async () => {
    const serialized = await this.model.serializeClientEvent(event);
    if (serialized != null) this.sendRaw(serialized);   // null = drop silently
  })
  .catch(error => { this.onError(...); });              // chain NEVER rejects
// Track the socket immediately (not just in `onopen`) so that calling
// `disconnect()` while it is still connecting actually closes it.
ws.onopen = () => { if (this.ws !== ws) return; onOpen(); };   // stale-open guard
ws.onclose = () => { if (this.ws === ws) { this.ws = null; this.onClose(); } };
...
if (this.model.getHealthCheckResponse != null) {
  const autoResponse = this.model.getHealthCheckResponse(rawEvent);
  if (autoResponse != null) this.sendRaw(autoResponse);  // ping pong before parse
}
```

**Flow:** every outbound event appends to a self-replacing promise chain, so async per-event serialization can never reorder writes; a failing serialization is caught INTO the chain (logged via onError) so one bad event doesn't poison the queue → connect assigns `this.ws` SYNCHRONOUSLY and every callback (open/close) verifies `this.ws === ws` identity before acting, so a replaced/closed socket's late events are ignored → inbound: normalize Blob/ArrayBuffer to text → `safeParseJSON` (parse failure silently ignored) → provider health-check hook answers pings BEFORE full event parsing → `parseServerEvent` may return an array (batch fan-out) or single event, each awaited in order through `onServerEvent`.
**Invariant:** The queue must catch its own errors — an unhandled rejection would permanently stall all subsequent sends. Socket-identity checks exist because WS callbacks fire for DEAD sockets after reconnect; the comment at :45–48 documents that tracking only at `onopen` lets a session-update fire against a disconnected session. Health checks bypass parse so unknown ping shapes never error.
**Probe:** deterministic: `grep -n "sendQueue = this.sendQueue" packages/ai/src/realtime/browser-realtime-transport.ts` → `79:`; `grep -n "if (this.ws !== ws) return;" packages/ai/src/realtime/browser-realtime-transport.ts` → `53:`; `grep -c getHealthCheckResponse packages/ai/src/realtime/browser-realtime-transport.ts` → `2`. Direct tests: `browser-realtime-transport.test.ts:50` closes connecting socket on disconnect, `:121` preserves order under async serialization, `:170` raw vs JSON-encoded payloads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "sendQueue serializeClientEvent", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: resolves the transport chain; rank#1 GatewayRealtimeModel.serializeClientEvent :93-96 (the serializer being awaited)
```

## Verdict
Adopt promise-chained ordered sends, synchronous socket tracking with identity guards, and pre-parse health-check interception; adapt serialization to your model adapter; omit nothing — naive `ws.send` ports reorder under async codecs and leak ghost-socket callbacks.
