<!-- capsule-v2 -->
# Fake SSE server contract — how do you fake a stateful HTTP+SSE MCP server so every client failure mode is injectable?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A client speaks MCP over HTTP+SSE to a remote IDE server. Testing its contract (handshake, auth, framing, response adoption, timeouts) against a real IDE is slow and uninjectable. What does a protocol fake owe the test author so every failure mode is a one-line option?

## One fake server, six fault-injection knobs, a request ledger, and a bounded close
**Path/Symbol:** `test/unit/helpers/fake-sse-server.ts` (whole, 160L) — options type :11-21, state shape :23-33, `createFakeSseServer` :35+, auth check :57-66, GET /sse handler :68-88, POST /message handler :90-133, bind + close :135-160.
**Signature:** `export function createFakeSseServer(options: FakeSseOptions = {}): Promise<FakeSseServer>` where `FakeSseOptions = { tools?, respondInPostBody?, callResult?, endpointDelayMs?, dropEndpointEvent?, neverRespondCalls?, crlf?, authToken? }` and `FakeSseServer = { port, baseUrl, requests: Array<{method, body, path, headers}>, sseConnections, close(): Promise<void> }`.
**Data Shape:** defaults make the happy path zero-config: one tool `open_file_in_editor`, `callResult = {content:[{type:'text',text:'sse-ok'}]}`, LF framing, no auth. The fake implements exactly the IntelliJ MCP surface: GET /sse (heartbeats + `endpoint` event), POST /message (JSON-RPC; notifications → 202 empty; initialize/tools-list/tools-call canned; responses pushed over the SSE stream by default).

### Decisive source
```ts
// :11-21 — every knob is a named failure mode of the real server
export type FakeSseOptions = {
  tools?: FakeSseTool[]
  respondInPostBody?: boolean   // adopt-response-in-POST-body mode vs SSE push
  callResult?: unknown          // canned tools/call result
  endpointDelayMs?: number      // delay the endpoint event → client handshake timeout path
  dropEndpointEvent?: boolean   // never send endpoint → client cannot POST at all
  neverRespondCalls?: boolean   // accept tools/call (202) but never reply → client timeout path
  crlf?: boolean                // \r\n framing → client SSE parser tolerance
  authToken?: string            // require BOTH IJ_MCP_AUTH_TOKEN and Bearer headers; else 401
}
```

**Flow:** bind on `127.0.0.1:0` (ephemeral, loopback-pinned like the real server) → GET /sse writes `: heartbeat` then the `event: endpoint` frame (unless dropped/delayed) and registers the connection → POST /message accumulates the body, records it in `requests[]`, returns 400 on bad JSON, 202 for notifications, and for requests either answers in the POST body (`respondInPostBody`) or 202s and pushes `{jsonrpc, id, result}` over EVERY open SSE connection. Auth (when `authToken` set) demands BOTH `ij_mcp_auth_token === token` AND `authorization === Bearer <token>` on EVERY request, else 401 with the real server's restricted-mode message. `close()` ends all SSE connections, closes the server with a 300ms unref'd fallback, then `closeAllConnections()` — no dangling handles between tests.
**Invariant:** the fake never invents protocol behavior the real server lacks: the dual-header auth requirement, the endpoint-event handshake, notification-202 semantics, and the restricted-mode 401 text all mirror `src/acp/mcp-sse.ts`'s client expectations (owned by sse-mcp-client-contract.md). The `requests` ledger makes assertions on wire shape (headers, paths, bodies) possible without touching the client.
**Probe:** `node --import tsx --test test/unit/mcp-sse.test.ts` — 13 tests built on this helper (POST-body adoption, CRLF, stream-end rejection, connect phase, dual auth headers, HTTP 401, timeout, idempotent close), executed GREEN at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "createFakeSseServer FakeSseOptions endpoint event respondInPostBody", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the knob-per-failure-mode fake design: one helper, every protocol failure mode a named boolean/number option, a request ledger for wire assertions, loopback ephemeral bind, and a bounded close that cannot leak handles. Adapt the canned methods and auth header names to your protocol. Omit the IntelliJ-specific endpoint-event shape only if your server pushes responses differently — but keep the respondInPostBody toggle if your client must adopt both transports. Direct tests executed green at the pin (13/13).
