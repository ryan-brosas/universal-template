<!-- capsule-v2 -->
# Streamable HTTP Transport & Session Lifecycle

**Source:** typescript-sdk MIT `main@HEAD`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does an MCP streamable HTTP transport manage session lifecycles, event replay, and SSE reconnection?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/streamableHttp.ts`: `validateSession` (:998-1038), `send` (:1144-1172); `packages/client/src/client/streamableHttp.ts`: `reconnect` (:726-777).
**Signature:** `validateSession(sessionId: string | undefined): void`
**Data Shape:** Server generates `Mcp-Session-Id` header (UUID string) on handshake; events carry `{ id: string, event: string, data: string }`.

### Decisive source
```ts
// Session validation asymmetry: missing header = 400, unknown session = 404.
// Replay stores events BEFORE delivery to support disconnected clients on Last-Event-ID.
export function validateSession(sessionId: string | undefined, activeSessions: Map<string, SessionState>): void {
  if (!sessionId) {
    throw new McpError(-32000, "Mcp-Session-Id header is required"); // 400 Bad Request
  }
  if (!activeSessions.has(sessionId)) {
    throw new McpError(-32001, "Session not found"); // 404 Not Found
  }
}
```

**Flow:**
1. Server mints `Mcp-Session-Id` upon receiving `initialize` request; client adopts it once handshake succeeds.
2. Subsequent requests check the session: missing ID returns 400; unlisted ID returns 404.
3. Outbound events are written to the durable `eventStore` *before* attempting live SSE socket delivery.
4. If the client disconnects, it reconnects using `Last-Event-ID` to replay missed events from the store.
5. GET opens a single standalone SSE stream; concurrent second GET returns `409 Conflict`.

**Invariant:**
- Storage is keyed on logical in-flight requests, not on whether a live SSE writer currently exists.
- Clean client aborts suppress error emission and do not attempt SSE reconnections.
- Teardown cancel closures verify the stored controller by reference identity before deleting the mapping.

**Probe:** `test/server/streamableHttp.test.ts` (asserts 400 for missing header, 404 for stale session ID, 409 for duplicate GET stream).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateSession streamableHttp eventStore Last-Event-ID", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the store-first event emission, session validation asymmetry (400 vs 404), and identity-checked teardown logic; adapt HTTP framework adapters.
