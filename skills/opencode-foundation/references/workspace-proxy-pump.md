<!-- capsule-v2 -->
# Workspace proxy pump — how do you transparently proxy HTTP and WebSocket traffic to a remote workspace without corrupting framing, leaking hop headers, or hiding upstream errors?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** When a request resolves to a Remote workspace plan (pass-6 workspace-routing capsule), what exactly must a bidirectional proxy do to headers, bodies, close codes, and error visibility so clients cannot tell it is proxied?

## Hop-header sanitize + dual-pump proxy with local 5xx logging
**Path/Symbol:** `packages/opencode/src/server/proxy-util.ts` (whole, 48L: `hop` :1-12, `sanitize` :14-18, `headers` :21-31, `websocketProtocols` :32-39, `websocketTargetURL` :41-46) + `packages/opencode/src/server/routes/instance/httpapi/middleware/proxy.ts` (`requestBody` :7-13, `websocket` :14-81, `http` :83-129).
**Signature:** `headers(input: Request|HeadersInit|Record<string,string>, extra?: HeadersInit) → Headers`; `websocket(request, target) → Effect<HttpServerResponse, never, WebSocketConstructor>`; `http(client, url, extra, request) → Effect<HttpServerResponse>`.
**Data Shape:** sanitize set = RFC 7230 hop-by-hop list (connection, keep-alive, proxy-authenticate, proxy-authorization, proxy-connection, te, trailer, transfer-encoding, upgrade) + host + accept-encoding + x-opencode-directory + x-opencode-workspace; `extra` (target auth headers) applied AFTER sanitize so they can override. Response side drops content-encoding + content-length (Effect re-encodes the stream).

### Decisive source
```ts
// proxy-util.ts:14-18 — hop-by-hop AND routing-context headers never cross the boundary:
function sanitize(out: Headers) {
  for (const key of hop) out.delete(key)
  out.delete("accept-encoding")
  out.delete("x-opencode-directory")
  out.delete("x-opencode-workspace")
}
// middleware/proxy.ts:55-62 — upstream socket errors keep their CLOSE CODE:
.runRaw((message) => writeInbound(message)).pipe(
  Effect.catchReason("SocketError", "SocketCloseError", (reason) =>
    writeInbound(new Socket.CloseEvent(reason.code, reason.closeReason)).pipe(Effect.catch(() => Effect.void))),
  Effect.catch(() => writeInbound(new Socket.CloseEvent(1011, "proxy error")).pipe(Effect.catch(() => Effect.void))),
  Effect.forkScoped,
)
// middleware/proxy.ts:66-70 — inbound binary frames are COPIED before forwarding:
return writeOutbound(typeof message === "string" ? message : message.slice())
// middleware/proxy.ts:105-121 — upstream 5xx is buffered, logged LOCALLY, forwarded unchanged:
if (response.status >= 500) {
  const body = yield* response.text.pipe(Effect.catch(() => Effect.succeed("")))
  ...
  yield* Effect.logError("workspace proxy upstream error", { url, method, status, body: body.slice(0, 2000) })
  return HttpServerResponse.text(body, { status, statusText, headers, contentType })
}
```

**Flow:** HTTP path: rebuild the request body from the incoming stream (GET/HEAD → empty; content-length taken from the header), send with sanitized headers + extra target auth; response headers drop content-encoding/content-length; status ≥ 500 ⇒ buffer the body, log it locally (first 2000 chars — the real cause lives only inside the remote sandbox), forward the body UNCHANGED with its original content-type so clients can still parse structured errors including their `ref`; otherwise stream through with `Stream.catchCause(() => Stream.empty)`; total failure degrades to an empty 500 (:128). WS path: convert target URL http→ws / https→wss, forward the sec-websocket-protocol list (CSV parsed, trimmed, empties dropped); register BOTH sockets' close-effects in the WebSocketTracker (unregistered ⇒ server closing ⇒ closeAccepted both sides, each with a 1s timeout); outbound pump forwards messages raw and maps upstream close reasons to the client's close code (other errors → 1011 "proxy error"); inbound pump copies binary frames before writing; either side finishing ends the connection.
**Invariant:** Hop-by-hop and routing-context headers (x-opencode-*) never reach the remote; the client's close code must reflect the UPSTREAM close reason, not a generic proxy failure; binary frames must be copied across the async write (no buffer reuse); an upstream 5xx body must arrive byte-identical so client error parsers still work, while its cause is logged on the HOST side where operators can see it.
**Probe:** `packages/opencode/test/server/proxy-util.test.ts` (whole, 113L — pins hop-header stripping incl. x-opencode-directory/workspace, extra-header override order, protocol CSV parsing with trim/filter, http→ws and https→wss conversion preserving query params); `test/server/httpapi-workspace-routing.test.ts:330-390` (pass-6 citation: end-to-end remote response fence consumption through this proxy); source pin:
```bash
grep -n 'message.slice()' packages/opencode/src/server/routes/instance/httpapi/middleware/proxy.ts
grep -n 'body.slice(0, 2000)' packages/opencode/src/server/routes/instance/httpapi/middleware/proxy.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "HttpApiProxy websocket http ProxyUtil headers sanitize websocketTargetURL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit hop-by-hop + context-header deny list with post-sanitize extra-header override for any reverse proxy that injects target credentials; adopt reason-code-preserving close propagation plus a distinct 1011 bucket for proxy-side failures; adopt local logging of buffered upstream 5xx bodies with byte-identical forwarding; adopt the binary-frame copy before async write. Adapt the deny list to your own context headers and the log truncation budget; omit opencode's specific tracker integration if your shutdown path differs. Direct test read whole (proxy-util.test.ts 113L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
