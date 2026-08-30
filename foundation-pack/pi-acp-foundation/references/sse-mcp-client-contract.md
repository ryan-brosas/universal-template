<!-- capsule-v2 -->
# SSE MCP client contract — how do you speak MCP over HTTP+SSE to a loopback IDE server, and why must request() return the deferred promise directly?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you implement an MCP client over HTTP+SSE for a loopback IDE server — endpoint-event handshake, auth headers, CRLF framing — and why must `request()` return the deferred promise directly instead of wrapping it in an async function?

## SSE MCP client contract
**Path/Symbol:** `src/acp/mcp-sse.ts` whole file (339L): `SseMcpPhase` :5-13, `SseMcpError` :16-27, `SseMcpClient` :35-339 (`#connect` :184-226, `#readStream` :228-300, `#handleMessage` :302-317, `#post` :319-338, `request` :88-128, `close` :153-166, `#authHeaders` :168-181).
**Signature:** `static async start(port: number, options?: { authToken?: string; onNotification? }): Promise<SseMcpClient>`; `request(method, params, timeoutMs, requestId?, onRequestId?): Promise<unknown>` (NOT async); `notify(method, params): Promise<void>`; `cancel(requestId): void`; `close(): Promise<void>`.
**Data Shape:** `SseMcpPhase = 'connect'|'endpoint'|'initialize'|'initialized_notification'|'tools_list'|'runtime_call'|'close'`; `SseMcpError` carries `{phase, status?}`. `DEFAULT_SSE_TIMEOUT_MS = 10_000` (endpoint-event wait). Base URL pinned to `http://127.0.0.1:<port>`.

### Decisive source
```ts
// request() returns the deferred promise DIRECTLY — the comment is the invariant:
// "Returns the deferred promise directly (not an async-function wrapper) so
// stream-end rejections land on the exact promise callers hold — an async
// wrapper would otherwise produce a transient unhandled rejection during
// promise adoption."
request(method, params, timeoutMs, requestId?, onRequestId?): Promise<unknown> {
  if (this.#closed) return Promise.reject(new SseMcpError('runtime_call', 'MCP SSE server is closed'))
  ...
  return promise
}
// endpoint event: resolve waiters ONLY for loopback — refuse off-loopback redirects
const resolved = new URL(payload, this.#baseUrl)
if (resolved.hostname !== '127.0.0.1' && resolved.hostname !== 'localhost' && resolved.hostname !== '[::1]')
  throw new SseMcpError('endpoint', `MCP SSE endpoint event points off-loopback (${resolved.hostname})`)
// dual auth headers: IDE-private token AND standard Bearer for servers accepting either
return { authorization: `Bearer ${this.#authToken}`, IJ_MCP_AUTH_TOKEN: this.#authToken }
// CRLF tolerance: "The SSE spec permits CRLF, LF, or CR line endings; IntelliJ sends CRLF."
buffer = buffer.replace(/\r\n|\r/g, '\n')
```

**Flow:** `start` → `#connect`: GET `/sse` with `accept: text/event-stream` + auth headers; non-OK → phase-`connect` `SseMcpError` with HTTP status (401 pinned by test). The stream reader starts immediately; the `endpoint` SSE event announces the message POST URL, which must resolve to loopback or the connect fails; `#endpointWaiters` resolve the handshake (10s timeout). Requests POST to the message URL; the response may be `202 Accepted` (reply arrives on the SSE stream) or carry the JSON-RPC response in the POST body (adopted directly, test-pinned). `#readStream` normalizes CRLF/CR→LF, splits on blank lines, parses `event:`/`data:` fields, and converges natural stream END and mid-stream ERROR on one failure path (`streamFailure ?? 'stream ended unexpectedly'`) that fails all pending requests unless close already did. Server-originated requests get a `-32601` echo. `close` aborts the controller, fails pending with phase-`close`, and races `#streamDone` against 500ms.
**Invariant:** a stream-end rejection must land on the exact promise the caller holds — an `async` wrapper around `request()` would adopt the rejection one microtask late and produce a transient unhandled rejection; off-loopback endpoint redirects are refused, never followed; auth headers ride BOTH the SSE connect and every POST.
**Probe:** `test/unit/mcp-sse.test.ts` (13 tests, read WHOLE this pass): POST-body adoption, CRLF framing, stream-end rejection of pending, connect-failure phase, dual auth headers on connect+POST (`ij_mcp_auth_token` + `authorization` asserted), HTTP 401 phase-`connect` failure, timeout, idempotent close. Executed GREEN at this pin in earlier passes (pass-7 fleet).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "SseMcpClient endpoint event off-loopback IJ_MCP_AUTH_TOKEN readStream", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deferred-promise-directly `request()` (the unhandled-rejection avoidance is the non-obvious part), the loopback-pinned endpoint-event handshake, dual auth headers, CRLF normalization, and the end/error convergence in the stream reader. Adapt phase names and the auth-header pair to your IDE. Omit the IntelliJ-specific `IJ_MCP_SERVER_PORT` launcher-fallback rationale if your host has no launcher-script quirk. Direct tests exist and were executed green at the pin.
