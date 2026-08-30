<!-- capsule-v2 -->
# tools/list_changed surfacing — how do you tell a client its tool catalog went stale when your catalog is an immutable session snapshot?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** When a bridged MCP server announces `notifications/tools/list_changed` mid-session, what should an adapter whose catalog is fixed at session start do?

## Once-per-session session_info_update notice
**Path/Symbol:** `src/acp/session.ts` (`handleIncomingMcpMessage` rewrite :360-385, `listChangedSurfaced` latch :406-407) + `src/acp/mcp-bridge.ts` (`LIST_CHANGED_DIAGNOSTIC` constant :26-27, both notification sites :384-390 / :718-720).
**Signature:** `async handleIncomingMcpMessage(params: Record<string, unknown>, notification: boolean): Promise<Record<string, unknown>>`.
**Data Shape:** single shared diagnostic string `'IDE bridge: tools/list_changed advertised; catalog is a session snapshot'` used by BOTH the server-notification handler and the client-notification path so dedupe works across paths (F-023); client-facing `_meta.piAcp.mcp` message names the remedy: "start a new chat to refresh".

### Decisive source
```ts
const before = this.bridge.diagnostics.length
const result = await this.bridge.handleIncomingMcpMessage(params, notification)
if (notification && String(params?.method ?? '') === 'notifications/tools/list_changed') {
  if (this.bridge.diagnostics.length > before && !this.listChangedSurfaced) {
    this.listChangedSurfaced = true
    this.emit({ sessionUpdate: 'session_info_update', _meta: { piAcp: { mcp: '…start a new chat to refresh (F-023)' } } })
  }
}
```

**Flow:** diagnostics-length delta (not string matching) detects that THIS notification actually registered — avoids double-surfacing when the diagnostic already existed; the once-latch (`listChangedSurfaced`) guarantees at most one client notice per session even if multiple servers announce changes. The catalog itself is NOT rebuilt: it stays an immutable per-session snapshot by design.
**Invariant:** never surface on startup-time notifications (only post-startup incoming messages flow through this method); at-most-once emission per session; catalog immutability is preserved — staleness is communicated, not papered over with a live refresh.
**Probe:** `npx tsx --test test/unit/mcp-bridge.test.ts` (bridge notification/diagnostic behavior) — executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "handleIncomingMcpMessage listChanged LIST_CHANGED_DIAGNOSTIC", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-catalog + once-per-session staleness notice via diagnostics-delta detection. Adapt the update type and message channel to your protocol. Omit if your bridge rebuilds catalogs live. Direct tests executed green at pin.
