<!-- capsule-v2 -->
# Streamable HTTP session host — how does an express host multiplex per-session transports on one /mcp route without race conditions?

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** What is the request-routing and lifecycle order that keeps transport maps, initialization, and shutdown consistent?

## Map sessionId→transport; connect BEFORE handling the initializing POST
**Path/Symbol:** `src/everything/transports/streamableHttp.ts` (`InMemoryEventStore` :11–37 store/replay for SSE resumability; CORS setup :42–51 exposing `mcp-session-id`, `last-event-id`, `mcp-protocol-version`; `transports: Map<string, StreamableHTTPServerTransport>` :54–57; POST handler :60–134; GET :137–162; DELETE :165–198; SIGINT sweep :224–240).

**Signature:** `app.post("/mcp", async (req, res) => void)` with branches keyed on presence+membership of header `mcp-session-id`.

### Decisive source
```ts
// src/everything/transports/streamableHttp.ts:71-103 — new-session branch
} else if (!sessionId) {
  const { server, cleanup } = createServer();
  const eventStore = new InMemoryEventStore();
  transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: () => randomUUID(),
    eventStore,                       // enables resumability replay
    onsessioninitialized: (sessionId: string) => {
      // Store the transport by session ID when a session is initialized.
      // This avoids race conditions where requests might come in before
      // the session is stored.
      transports.set(sessionId, transport);
    },
  });
  server.server.onclose = async () => {         // teardown mirror:
    const sid = transport.sessionId;
    if (sid && transports.has(sid)) {           // remove from map,
      transports.delete(sid);                   // then run factory cleanup
      cleanup(sid);
    }
  };
  // Connect the transport to the MCP server BEFORE handling the request
  // so responses can flow back through the same transport.
  await server.connect(transport);
  await transport.handleRequest(req, res);
  return;
}
```

**Flow:** every POST → existing sessionId in map ⇒ reuse that transport (`handleRequest`); no sessionId ⇒ treat as initialization (fresh factory + transport, register via `onsessioninitialized`, connect-then-handle); sessionId but unknown ⇒ HTTP 400 JSON-RPC error `-32000 "Bad Request: No valid session ID provided"`. GET streams and DELETE termination look up the same map. Uncaught handler errors answer 500 `-32603` only when headers aren't already sent (:120–132). Shutdown closes every live transport before `process.exit(0)`.

**Invariant:** registration into the map happens inside `onsessioninitialized` — NOT after `handleRequest` returns — because concurrent requests can arrive mid-initialization; a porter who inserts after handling drops those requests. Symmetrically, `onclose` must both delete from the map AND invoke factory `cleanup`, or timers outlive the session.

**Probe:** `src/everything/__tests__/server.test.ts` pins factory-level contracts (`oninitialized` set, cleanup present); the express wiring itself is exercised by Inspector integration rather than unit tests — recorded as a coverage caveat; the deterministic anchors here are the source ordering above plus the SDK's `StreamableHTTPServerTransport` contract it depends on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "StreamableHTTPServerTransport transports map onsessioninitialized handleRequest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-branch POST router (reuse / initialize-with-connect-before-handle / 400), init-time map insertion via callback, symmetric onclose deletion + cleanup, and the shutdown sweep; adapt to your HTTP framework and replace the in-memory event store with durable storage for production resumability; omit GET/DELETE routes when targeting the modern spec revision where they are removed.
