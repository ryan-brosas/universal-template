<!-- capsule-v2 -->
# Dual-plane gateway — how does one WebSocket entrypoint serve both single-instance and Redis-clustered modes?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How does the gateway decide between handing a socket straight to hocuspocus and routing it through the RedisSync proxy plane, and what does the serialized request have to preserve?

## CollaborationGateway.handleConnection
**Path/Symbol:** `apps/server/src/collaboration/collaboration.gateway.ts`:`handleConnection` / `serializeRequest` (lines 85–134); hocuspocus tuning (lines 49–58).
**Signature:** `handleConnection(client: WebSocket, request: IncomingMessage): any`; `serializeRequest(request: IncomingMessage): SerializedHTTPRequest`.
**Data Shape:** Serialized form keeps ONLY what survives JSON/msgpack: method, url, `sec-websocket-key`, `sec-websocket-protocol`, socket.remoteAddress — with `?? ''` defaults so nothing is undefined across the wire.

### Decisive source
```ts
if (this.redisSync) {
  const wrappedSocket = new WsSocketWrapper(client);
  // Route through RedisSync extension (this calls handleConnection internally)
  this.redisSync.onSocketOpen(wrappedSocket, serializedHTTPRequest);
  client.on('message', (data) => this.redisSync!.onSocketMessage(serializedHTTPRequest, data));
  client.on('close',  (code, reason) => this.redisSync!.onSocketClose(socketId, code, new Uint8Array(reason).buffer));
} else {
  const clientConnection = this.hocuspocus.handleConnection(client, toWebRequest(this.serializeRequest(request)));
  client.on('message', (data) => clientConnection.handleMessage(new Uint8Array(data)));
}
```
Tuning that shapes the whole pipeline: `{ debounce: 10000, maxDebounce: 45000, unloadImmediately: false }`.

**Flow:** ws 'connection' → redis mode: wrap socket write-side only, register origin connection, forward message/close events into the extension : standalone mode: direct handleConnection. The WsSocketWrapper exists because incoming events are forwarded by the gateway — letting hocuspocus ALSO subscribe would double-handle every frame.
**Invariant:** in redis mode the raw ws client's events must flow ONLY through RedisSyncExtension (`onSocketOpen/onSocketMessage/onSocketClose`), never also through `hocuspocus.handleConnection` on the origin — double registration corrupts session state. The serialization whitelist is the contract for what auth can see after crossing Redis.
**Probe:** `grep -cF 'this.redisSync.onSocketOpen' apps/server/src/collaboration/collaboration.gateway.ts` (=1) and `grep -cF 'debounce: 10000,' apps/server/src/collaboration/collaboration.gateway.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "CollaborationGateway handleConnection serializeRequest WsSocketWrapper", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode-switch at a single connection entrypoint + minimal serialized-request identity; adapt to your WS server; omit hocuspocus classes if using another CRDT runtime. No upstream direct test; pinned by source read + probes.
