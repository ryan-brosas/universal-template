<!-- capsule-v2 -->
# Legacy SSE transport twin — how does the deprecated HTTP+SSE host pair a GET stream with POST /message, per session?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** How do you wire the LEGACY (pre-2025-03-26) SSE transport — one server instance + outbound stream per client — and which reconnect mistakes does the reference code warn about?

## Per-session server map keyed on transport sessionId
**Path/Symbol:** `src/everything/transports/sse.ts` (whole file: CORS :9–17; `transports` map :19–23; GET `/sse` handler :26–56; POST `/message` handler :59–71; listen :74–77). Uses SDK's `SSEServerTransport("\/message", res)` (:40) — first arg is the POST endpoint path the client is told to message.

**Signature:** state = `Map<string, SSEServerTransport>` from `transport.sessionId` → live transport. One `createServer()` (fresh McpServer + cleanup closure, see `server-factory`) PER CONNECTION inside the GET handler (:28), never shared.

### Decisive source
```ts
// src/everything/transports/sse.ts:26-55 (condensed)
app.get("/sse", async (req, res) => {
  let transport: SSEServerTransport;
  const { server, cleanup } = createServer();          // NEW server per connection
  if (req?.query?.sessionId) {                          // a returning session must NOT hit /sse again
    transport = transports.get(sessionId) as SSEServerTransport;
    console.error(
      "Client Reconnecting? This shouldn't happen; when client has a sessionId, GET /sse should not be called again.",
      transport.sessionId);
  } else {
    transport = new SSEServerTransport("/message", res);
    transports.set(transport.sessionId, transport);
    await server.connect(transport);
    server.server.onclose = async () => {
      transports.delete(transport.sessionId);           // reap map entry...
      cleanup(transport.sessionId);                     // ...and run the factory cleanup
    };
  }
});
app.post("/message", async (req, res) => {
  const sessionId = req?.query?.sessionId as string;    // inbound messages carry ?sessionId=
  const transport = transports.get(sessionId);
  if (transport) await transport.handlePostMessage(req, res);
  else console.error(`No transport found for sessionId ${sessionId}`);   // silent-ish miss
});
```

**Flow:** client opens `GET /sse` → no sessionId ⇒ mint transport (which generates the sessionId), store it, connect the fresh server instance, register `onclose` reaper → later JSON-RPC messages arrive as `POST /message?sessionId=...` → route to that transport's `handlePostMessage`. Disconnect fires `onclose` ⇒ delete map entry + cleanup closure. CORS is permissive `origin: "*"` explicitly for Inspector direct-connect testing (:8–16 comment: use "*" with caution in production).

**Invariant:** the GET endpoint is SESSION-CREATION only — a client re-GETting with an existing sessionId is a protocol misuse the reference deliberately logs ("This shouldn't happen") instead of silently creating a second stream for the same session. Every session gets its OWN server instance (per-session isolation of tools/state); sharing one McpServer across transports would cross-wire notifications. Unknown-session POSTs are logged and dropped without a 4xx — the reference chooses liveness over strict rejection here. This transport is DEPRECATED (see `deprecated-features-registry`, SEP-2577/2596 horizon): port it only to serve legacy clients.

**Probe:** `src/everything/__tests__/` covers the server factory and tool/prompt surfaces but has NO test instantiating `transports/sse.ts` (coverage caveat recorded honestly — this file is exercised by Inspector manual testing, not vitest).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", qn_pattern: "transports.sse|transports.stdio", limit: 10 });
```

## Verdict
Adopt the one-server-one-stream-per-session shape, sessionId-keyed transport map, and onclose reaper+cleanup pairing when you must serve legacy SSE clients; adapt the express host and CORS posture (never ship `origin:"*"` in production); omit this pattern entirely for modern servers — Streamable HTTP (`streamable-http` capsule) replaced it.
