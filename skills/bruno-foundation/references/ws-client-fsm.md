<!-- capsule-v2 -->
# WebSocket client connection FSM — close-promise coalescing, orphan-queue discipline, and identity-checked close events

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How does a long-lived WS client make connect/close/send races deterministic — reusing CONNECTING sockets, coalescing closes, and never flushing a queue onto a dead socket?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/ws/ws-client.js:WsClient` (whole 514L — `startConnection` :70, `close` :216, `closeForCollection` :288, `#setupWsEventHandlers` :335, `#detachSocket` :448, `#forgetRequest` :484, `connectionStatus` :505).
**Signature:** `startConnection({request, collection, options}) → Promise<WebSocket>; close(requestId, code=1000, reason) → Promise<void>`.
**Data Shape:** four keyed maps: `activeConnections: Map<requestId,{collectionUid,connection}>`, `closingResolvers: Map<requestId,{resolve,timeoutId,promise}>`, `messageQueues: {requestId: {collectionUid, messages:[{message,format}]}}`, `connectionKeepAlive: Map<requestId, timer>`; per-(request,collection) message sequencer.

### Decisive source
```js
// Wait out an in-flight close so we don't open a replacement that the close handler then deletes.
if (this.closingResolvers.has(requestId)) {
  await this.closingResolvers.get(requestId).promise;
}
// Reuse in-flight / open socket so ensure+connect races don't open a second connection.
const meta = this.activeConnections.get(requestId);
const existing = meta?.connection;
if (existing && (existing.readyState === ws.WebSocket.CONNECTING || existing.readyState === ws.WebSocket.OPEN)) {
  return existing;
}
```

**Flow:** startConnection ⇒ await in-flight close → reuse CONNECTING/OPEN socket → else build (`ws` needs protocols pre-split on commas; protocolVersion force-numbered) → register handlers + emit connecting. `close` ⇒ return existing close promise if in flight → drop queue BEFORE handshake (a late `open` must not flush) → emit disconnecting → arm 5s safety timeout that terminates + emits synthetic close(1006) BEFORE forgetting → send real close frame. Socket `close` event ⇒ resolve pending close promise first, then IDENTITY CHECK: `activeConnections.get(requestId)?.connection !== ws` means this is a timed-out/replaced socket — swallow its event so it can't remove the replacement. `open` flushes queued messages only if still live.
**Invariant:** every teardown path funnels through `#clearClientState` (keepalive timer + queue) then `#forgetRequest` (sequencer + map delete + connections-changed emit); `#detachSocket` nulls `meta.connection` BEFORE terminate so a synchronous close event cannot re-enter `#forgetRequest` mid-teardown; status ladder is exactly `disconnecting > connecting > connected > disconnected`.
**Probe:** `packages/bruno-requests/src/ws/ws-client.spec.js` :91-272 — 'reuses an existing CONNECTING socket…', 'coalesces concurrent close calls onto one in-flight promise', 'resolves close after safety timeout if close event never fires', 'does not let a timed-out socket close remove a replacement connection', 'waits for an in-flight close before opening a new socket', 'drops a queued message when close is called with no live socket', 'does not flush an orphaned queue after the collection is closed' (each grep -c = 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "WsClient startConnection close closingResolvers", limit: 5 });
// resolves startConnection :70-149 / close :216-268 / closeForCollection :288-299
```

## Verdict
Adopt the whole FSM: single-close-promise coalescing with safety-timeout terminate, close-before-reuse awaiting, queue-drop-before-handshake, identity-checked late events. Adapt event names to your bus; omit hexdump/sequencer presentation details. Coverage caveat: none — clean coverage at pin.
