<!-- capsule-v2 -->
# Socket proxying — when a doc lives on another server, how does a client's byte stream reach it without a second WebSocket?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How do you relay Yjs traffic for a remote-owned doc over Redis pub/sub while keeping the client's single real socket alive?

## Origin/owner split with `CollabProxySocket`
**Path/Symbol:** `apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts`:`onSocketMessage` / `handleProxyMessage` / `closeProxy` (lines 336–402, 111–151); `apps/server/src/collaboration/extensions/redis-sync/collab-proxy-socket.ts`:`CollabProxySocket` (lines 7–46); `apps/server/src/collaboration/extensions/redis-sync/ws-socket-wrapper.ts`:`WsSocketWrapper` (lines 9–35).
**Signature:** `onSocketMessage(serializedHTTPRequest: SerializedHTTPRequest, detachableMsg: ArrayBuffer)`; `class CollabProxySocket implements WebSocketLike { send(message: Uint8Array): void; close(code?, reason?): void; markClosed(): void; }`.
**Data Shape:** Wire message `{type:'proxy', replyTo, message: Uint8Array, serializedHTTPRequest}` to channel `<prefix>Msg:<ownerServerId>`; replies `{type:'send', socketId, message}` and `{type:'close', code, reason, socketId}` back on `replyTo`. `socketId = headers['sec-websocket-key']`.

### Decisive source
```ts
const proxyTo = await this.getOrClaimLockThrottled(documentName);
if (proxyTo && proxyTo !== this.serverId) {
  // Proxied messages bypass handleMessage, so refresh the connection's
  // liveness fields manually or hocuspocus' message timeout would reap the
  // real socket every `timeout` ms. connectionEstablishedAt is the
  // reference while unauthenticated (auth for remote docs is proxied too)
  // and is private upstream.
  clientConnection.lastMessageReceivedAt = Date.now();
  (clientConnection as any).connectionEstablishedAt = Date.now();
  const proxyMessage: RSAMessageProxy = { serializedHTTPRequest, replyTo: `${this.msgChannel}:${this.serverId}`, message, type: 'proxy' };
  this.pub.publish(`${this.msgChannel}:${proxyTo}`, msg);
```
Owner side builds one `CollabProxySocket` per remote client (`readyState=1`, `send()` publishes `{type:'send'}`), feeds it plus `toWebRequest(serializedHTTPRequest)` into `instance.handleConnection`, so upstream runs its normal auth/load pipeline against a synthetic socket.

**Flow:** origin receives bytes → parses leading varString documentName (stripping `\0sessionId`) → local? deliver : claim-lock → owner? build proxy connection once per socketId, feed messages : publish `{type:'proxy'}` → owner writes back via `{type:'send'}` / `{type:'close'}` → origin closes real socket on genuine close codes only.
**Invariant:** the client keeps exactly ONE physical WebSocket (to the origin) no matter how many docs route elsewhere. Proxy-socket close with `code === ConnectionTimeout.code` must NOT be relayed — the timeout reaper would kill the client's real socket, which may carry other documents' sessions (`markClosed()` + silent dispose instead). Proxied messages bypass upstream liveness bookkeeping, so the origin must manually refresh `lastMessageReceivedAt`/`connectionEstablishedAt`.
**Probe:** `grep -cF 'ConnectionTimeout.code' apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts` (=1) and `grep -cF 'readyState !== 1' apps/server/src/collaboration/extensions/redis-sync/collab-proxy-socket.ts` (=2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "CollabProxySocket handleProxyMessage onSocketMessage proxy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the origin/owner split: serialize only the request identity (`sec-websocket-key`, url, headers, remoteAddress), rebuild a web-standard `Request` via `toWebRequest`, and synthesize an owner-side socket that publishes writes back. Adapt channel naming/packing; omit hocuspocus-specific `ClientConnection` internals. No upstream direct test; pinned by source read + probes.
