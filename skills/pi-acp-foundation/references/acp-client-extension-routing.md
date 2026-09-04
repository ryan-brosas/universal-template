<!-- capsule-v2 -->
# Client→agent extension routing — how do you route client→agent extension messages (mcp/message) to the owning session with the right method/notification asymmetry?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** The ACP SDK hands an agent implementation every client method it does not know via `extMethod`/`extNotification`. The adapter uses exactly one extension method — `mcp/message`, carrying a `connectionId` + inner MCP message for the IDE bridge. How do you expose that surface so unknown methods fail correctly, notifications never error, and each message lands on the session that owns the connection?

## Single-method allowlist with throw-vs-silent asymmetry and connectionId ownership scan
**Path/Symbol:** `src/acp/agent.ts:333-341` (`PiAcpAgent.extMethod`, `PiAcpAgent.extNotification`); `src/acp/session.ts:206-218` (`SessionManager.handleIncomingMcpMessage`); `src/acp/session.ts:357-384` (`PiAcpSession.ownsMcpConnection`, `PiAcpSession.handleIncomingMcpMessage`). The inner MCP transport flow (mcp/connect, mcp/message envelopes) is owned by `references/mcp-bridge-transports.md`; the post-delivery list_changed staleness notice is owned by `references/list-changed-surfacing.md`.
**Signature:** `extMethod(method: string, params: Record<string, unknown>): Promise<Record<string, unknown>>`; `extNotification(method: string, params: Record<string, unknown>): Promise<void>`; `handleIncomingMcpMessage(params: Record<string, unknown>, notification: boolean): Promise<Record<string, unknown>>`.
**Data Shape:** `params.connectionId` (string) identifies the bridge connection; `params.method`/`params.params` carry the inner MCP message; `notification: boolean` distinguishes request (must return a result) from notification (fire-and-forget). Failure shapes: thrown `Error` (SDK maps to a JSON-RPC error response for requests; notifications drop it).

### Decisive source
```ts
async extMethod(method: string, params: Record<string, unknown>): Promise<Record<string, unknown>> {
  if (method !== 'mcp/message') throw new Error(`Unsupported client extension method: ${method}`)
  return this.sessions.handleIncomingMcpMessage(params, false)
}

async extNotification(method: string, params: Record<string, unknown>): Promise<void> {
  if (method !== 'mcp/message') return          // silent: notifications are fire-and-forget
  await this.sessions.handleIncomingMcpMessage(params, true)
}
```
```ts
// SessionManager router — guard BEFORE scanning, ownership decides the session
const connectionId = params.connectionId
if (typeof connectionId !== 'string') throw new Error('mcp/message is missing connectionId')
for (const session of this.sessions.values()) {
  if (session.ownsMcpConnection(connectionId)) {
    return session.handleIncomingMcpMessage(params, notification)
  }
}
throw new Error(`Unknown MCP connection: ${connectionId}`)
```

**Flow:** ACP SDK dispatches an unknown client method → `extMethod` (request) or `extNotification` (notification). Both enforce the same single-method allowlist (`mcp/message`) but with opposite failure postures: a request for an unknown method THROWS (the client receives an error response — it asked, it must be told), a notification for an unknown method SILENTLY RETURNS (JSON-RPC notifications carry no response channel; erroring is meaningless and could crash well-behaved clients' send paths). The manager then validates `connectionId` is a string BEFORE iterating sessions, scans for the session whose bridge owns the connection (`bridge?.ownsConnection(connectionId) ?? false`), and throws on no owner. The owning session delegates to its bridge and — only for `notifications/tools/list_changed` — surfaces the once-per-session staleness notice (see list-changed-surfacing.md).
**Invariant:** exactly one extension method is accepted on both entry points; the request/notification asymmetry (throw vs silent) is preserved at the allowlist AND flows through as the `notification` flag into the bridge; a message can never be routed by anything but connection ownership — there is no fallback session, no broadcast, and a missing/non-string `connectionId` fails before any session is touched.
**Probe:** `test/unit/mcp-bridge.test.ts:391-426` pins the BRIDGE-level half: unsupported server-originated request (`sampling/createMessage`) → `{error:{code:-32601, message:'Unsupported server-originated MCP request: …'}}` with the catalog unchanged, and duplicate `tools/list_changed` notifications produce exactly one diagnostic (F-023 dedupe). Coverage caveat: the agent-level stubs (agent.ts:333-341) and the SessionManager router (session.ts:206-218) have NO direct test at this pin — their contract is pinned by source read + the SDK's dispatch semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "extMethod extNotification handleIncomingMcpMessage ownsMcpConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-method allowlist duplicated across both entry points, the throw-vs-silent asymmetry (requests must be answerable; notifications must never error), the guard-before-scan ordering on the routing key, and ownership-only routing with a hard throw on unknown connections. Adapt the allowlist when your protocol gains more extension methods — keep the per-method posture table explicit rather than inferring it from the entry point. Omit any broadcast/fallback routing: with per-session bridges, a misrouted MCP message is worse than a rejected one.
