<!-- capsule-v2 -->
# MCP manager diff-reconcile — how do config reloads add, remove, and update live server connections without dropping healthy ones?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When a reload produces a new list of MCP servers, how does a porter apply it to a pool of live connections so that unchanged servers never reconnect and stale ones always die?

## Three-way diff: remove-absent / add-missing / in-place option swap; refresh only when something changed

**Path/Symbol:** `core/context/mcp/MCPManagerSingleton.ts` whole (204 lines): `setConnections` (:68–109), `compareTransportOptions` (:111–128), `compareEnv` (:130–142), `shutdown` (:53–66), `refreshConnection` (:144–153), `refreshConnections` (:155–175).
**Signature:** `setConnections(servers: InternalMcpOptions[], forceRefresh: boolean, extras?: MCPExtras): void`; `compareTransportOptions(a, b): boolean`.
**Data Shape:** process-wide singleton holding `Map<serverId, MCPConnection>`; identity key is content-addressed upstream ("NOTE the id is made by stringifying the options"), so an options change yields a NEW id ⇒ old entry removed, new one added.

### Decisive source
```ts
// Remove any connections that are no longer in config (or whose transport changed)
if (!servers.find((s) => s.id === id && this.compareTransportOptions(connection.options, s))) {
  refresh = true;
  connection.abortController.abort();
  void connection.client.close();
  this.connections.delete(id);
}
// Unchanged servers: swap options IN PLACE — no reconnect
// We need to update it. Some attributes may have changed, such as name, faviconUrl, etc.
conn.options = server;
...
if (refresh) { void this.refreshConnections(forceRefresh); }
```

**Flow:** every compile-plane load ends with `mcpManager.setConnections(mcpOptions, false)` — verified drivers: `core/config/load.ts:544` (JSON plane) and `core/config/yaml/loadYaml.ts:380` (YAML plane, passes `{ ide }` extras); both NON-forced, so routine reloads never reconnect healthy servers. Transport equality decides "unchanged": type must match; stdio compares command + JSON-stringified args + env as an UNORDERED map (`compareEnv`); remote compares url only. If anything changed: removals abort+close+delete first, additions construct fresh `MCPConnection`s, then `refreshConnections(force)` fires fire-and-forget — it swaps the manager's own AbortController FIRST (killing the prior generation's listeners), then races an abort-listener promise against `Promise.all(connectClient(force, signal))`, invoking `onConnectionsRefreshed` only in the work branch (this callback is what triggers the "config reloaded again once connected" cycle). `refreshConnection(id)` is the single-server variant: throws shaped ``MCP Connection <id> not found`` on unknown id. `shutdown()` uses `Promise.allSettled` with delete-in-`finally`, so entries are removed even when `client.close()` throws.
**Invariant:** reconcile is idempotent under repeated identical configs (refresh flag stays false ⇒ zero reconnects); per-connection liveness changes are monotone-destructive (abort+close before delete); the manager never awaits its own refresh — callers get synchronous return and observe completion via `onConnectionsRefreshed`.
**Probe:** `core/context/mcp/MCPManagerSingleton.vitest.ts` (whole 195L): singleton identity (:65–71), create/get idempotence (:73–95), setConnections add (:97–104) and remove-with-abort+close-spies (:106–121), refreshConnection forced+signal (:124–137) and unknown-id rejection (:139–143), refreshConnections all + onConnectionsRefreshed callback (:146–179), getStatuses carries raw `client` (:181–194).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "MCP manager singleton setConnections reconcile refresh connections", limit: 10 });
```
(Graph caveat recorded this pass: `trace_path` inbound on `setConnections` returns `callers_total: 0` — both real drivers dispatch through the module singleton dynamically; verify consumers by direct read.)

## Verdict
Adopt diff-based reconcile keyed by transport equality, the in-place option swap for cosmetic-only changes, and refresh-only-if-changed; adapt equality to your transport tuple; omit the content-addressed id trick only if your ids are stable names (then compare ids AND transports). Trap: remote equality ignores headers — the OAuth bearer header added at connect time (see mcp-oauth-sse-token-plane.md) deliberately does NOT look like a transport change.
