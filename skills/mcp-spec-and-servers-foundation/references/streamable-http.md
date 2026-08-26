<!-- capsule-v2 -->
# Streamable HTTP transport — how do you host the modern MCP endpoint so every request is independent, header-consistent, and streamable?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What are the exact POST/response rules of the single MCP endpoint, which headers MUST mirror the body, and how does a client detect a legacy server?

## One endpoint, POST-everything, request-scoped streams
**Path/Symbol:** `docs/specification/draft/basic/transports/streamable-http.mdx` (endpoint rule :47–49; sending rules :70–105; receiving :107–157; message-flow diagrams :166–231; cancellation :233–242; request metadata + validation :244–648; backward compat :650–739).

### Decisive source
```md
# streamable-http.mdx:72-91 (the wire contract)
1. The client MUST use HTTP POST to send JSON-RPC messages.
2. The client MUST include an Accept header listing both application/json and
   text/event-stream as supported content types.
3. The client MUST include the request metadata headers on each POST request.
...
5. If the body is a JSON-RPC notification:
   - If the server accepts it, the server MUST return HTTP status code
     202 Accepted with no body.
6. If the body is a JSON-RPC request, the server MUST return either
   Content-Type: application/json (a single JSON object) or
   Content-Type: text/event-stream (an SSE response stream). The client
   MUST support both.
```
2026-07-28 revision changes (:14–25): GET stream endpoint REMOVED; protocol-level sessions (`Mcp-Session-Id`) REMOVED. Legacy traffic handling (:681–688): GET/DELETE ⇒ `405 Method Not Allowed`; `Mcp-Session-Id` header ⇒ ignore, never mint or echo one; `Last-Event-ID` ⇒ ignore (streams are not resumable).

**Header mirroring** (:286–308): `MCP-Protocol-Version: <version>` on EVERY POST and `Mcp-Method: <method>` REQUIRED; `Mcp-Name: params.name|params.uri` for tools/call, resources/read, prompts/get. Header values must match body values exactly; mismatch or missing ⇒ HTTP 400 + JSON-RPC `-32020 HeaderMismatch` (:597–609). Base64 sentinel `=?base64?{...}?=` carries non-ASCII/unsafe values; servers MUST decode before comparing (:467–508); plain-ASCII values that merely LOOK like sentinels MUST also be encoded (:506–508). Integer comparisons are numeric (`42.0` == `42`, :589–595). Intermediaries that don't recognize `Mcp-Param-*` MUST forward them (:548–550).

**SSE response stream** (:107–155): server MAY emit request-related notifications (`notifications/progress`, `notifications/message`) before the final response; MUST NOT send independent requests on it (MRTR replaced that); final response SHOULD terminate the stream; `X-Accel-Buffering: no` defeats proxy buffering; SSE comment lines (`:`) as keep-alive for long-lived streams; closing the response stream IS the cancellation signal — no `notifications/cancelled` over HTTP (:96–103, :233–242).

**Legacy-era fallback probe** (:650–668): POST a modern request; on `400 Bad Request` inspect the BODY — recognized modern errors (`UnsupportedProtocolVersionError`, `MissingRequiredClientCapabilityError`, header-validation) mean a MODERN server: retry with advertised versions. Empty/unrecognized body ⇒ legacy: fall back to `initialize`, possibly further to deprecated HTTP+SSE (GET expecting an `endpoint` event first, :720–738). Security baseline (:56–68): validate `Origin` (403 on invalid) against DNS rebinding; bind localhost locally.

**Invariant:** header-vs-body consistency is validated by any body-processing server because load balancers route on headers while servers execute on bodies — a porter who skips `-32020` validation lets the two sources of truth diverge. Every request is its own HTTP transaction; nothing may be cached between them.

**Probe:** no runtime test suite in the spec repo (docs+schema only); the machine-checkable anchors are the schema types these rules reference (`HeaderMismatchError` schema.ts :463+, `SubscriptionsListenRequest` :1314+) and `scripts/validate-examples.ts` validating bundled example payloads. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "MCP-Protocol-Version Mcp-Method Mcp-Name HeaderMismatch streamable http", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-endpoint POST-everything with dual Accept, per-request metadata headers + decode-before-compare validation returning `-32020`, request-scoped SSE with keep-alive comments, close-stream-means-cancelled, and body-inspection era probing; adapt origin allowlists, auth middleware, and proxy topology to your host; omit the removed GET-stream/session/Last-Event-ID machinery unless you deliberately serve the ≤2025-11-25 revisions.
