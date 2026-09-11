<!-- capsule-v2 -->
# GristSocketServer transport interception — how do raw WebSocket upgrades and Engine.IO long-polling share one verify-and-abstract seam in front of the realtime layer?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does a server intercept both `ws` upgrade requests and EIO polling HTTP requests, verify them once, and hand ONE socket abstraction to the app — including failure postures for closed servers and throwing verifiers?

## Middleware interception with destroyOnRejection armor; closed-server answers are made CONSISTENT instead of library-default
**Path/Symbol:** `app/server/lib/GristSocketServer.ts` — whole file (181L): `listen()` (:31–63), `close()` (:80–96), `handleHTTPUpgrade()` (:104–124), `handleHTTPRequest()` (:132–153), `_handleEIOConnection` (:155–159), `destroyOnRejection` (:168–177), `isPollingSocketRequest` (:17–19), `MAX_PAYLOAD = 100e6` (:11).
**Signature:** `handleHTTPUpgrade(req, socket: net.Socket, head: Buffer): Promise<boolean>`; `handleHTTPRequest(req, res): Promise<boolean>` (true = intercepted); `onconnection(handler: (socket: GristServerSocket, req) => void)`.
**Data Shape:** Two transports → one interface (`GristServerSocketWS` wraps `ws`; `GristServerSocketEIO` wraps engine.io polling). EIO configured `allowUpgrades:false, transports:["polling"]`, `maxHttpBufferSize = MAX_PAYLOAD`. Polling detection is a URL regex: `/[&?]transport=polling(&|$)/`.

### Decisive source
```ts
// GristSocketServer.ts:106-118 — verify-once, then consistent closed-state answers
return destroyOnRejection(socket, async () => {
  if (this._options?.verifyClient && !await this._options.verifyClient(req)) {
    terminateSocketWithHttpResponse(socket, 403, "forbidden");
    return true;
  }
  // If server is closed, make the response consistent by handling it here
  if (this._closed) {
    terminateSocketWithHttpResponse(socket, 503, "socket server is closed");
    return true;
  }
  this._wsServer.handleUpgrade(req, socket, head, (client) => {
    this._connectionHandler?.(new GristServerSocketWS(client), req);
  });
```

**Flow:** host http.Server routes upgrades to `handleHTTPUpgrade` and normal requests to `handleHTTPRequest` → polling-shaped requests are claimed; everything else returns false so Express owns it → verifyClient must NOT throw (contract in options docs); a rejection anywhere hits `destroyOnRejection`, which logs and destroys the socket — "a fallback; handlers should never throw" but an unhandled rejection would kill the process. CORS note (:44–55): EIO reflects ANY origin + credentials deliberately, because native WebSockets aren't covered by SOP and verification happens in verifyClient — the comment IS the security model. `close()` marks closed FIRST (no new handling), terminates every ws client explicitly (ws ≥4 stopped doing it in close()), and guards double closure from both HTTP-server-end and explicit close.
**Invariant:** The abstraction boundary is total — Comm.ts never sees which transport a client chose; adding a third transport means one more wrapper class, zero app changes. Closed-server 403/503 answers are produced BY THIS CLASS rather than letting ws/EIO defaults hang or mislead clients mid-restart.
**Probe:** `test/server/lib/GristSockets.ts` (:127 exposes initial request, :145 receive/send round-trip, :157 send callbacks, :168 close event, :177 "should fail gracefully if verifyClient throws exception"). Source pins: `grep -c 'destroyOnRejection' app/server/lib/GristSocketServer.ts` = 2 call sites + def; `grep -n 'transport=polling' app/server/lib/GristSocketServer.ts` = :18.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"GristSocketServer handleHTTPUpgrade handleHTTPRequest verifyClient polling","limit":10,"detail":"ids"}'
```

## Verdict
Adopt the two-transport/one-abstraction seam with middleware-style interception booleans and destroyOnRejection armor; adapt payload caps, polling regex, and the reflected-CORS rationale to your gateway; omit EIO specifics if you only need raw WS (keep the consistent-closed-answers contract). Direct mocha coverage at this pin; runner-blocked locally — probes recorded as source-pinned assertions.
