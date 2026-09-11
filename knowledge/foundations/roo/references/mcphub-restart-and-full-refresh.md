<!-- capsule-v2 -->
# restartConnection UX delay + refreshAllConnections full rebuild — how do you make a server restart visible to the user, and when must you rebuild ALL connections from scratch instead?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does a single-server restart preserve its config across teardown, and why does refreshAllConnections tear down everything before re-initializing?

## 500ms visible-restart pause; global refresh = wipe-all then re-init both sources
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`restartConnection` :1254–1294; `refreshAllConnections` :1296–1364; `handleMcpEnabledChange` :1901–1947).
**Signature:** `async restartConnection(serverName: string, source?: "global" | "project"): Promise<void>`.
**Data Shape:** restart reads `connection.server.config` (the stored JSON STRING) as its source of truth — deliberately NOT a live object — then re-validates it through `validateServerConfig` after delete.

### Decisive source
```ts
// :1268-1272
vscode.window.showInformationMessage(t("mcp:info.server_restarting", { serverName }))
connection.server.status = "connecting"
connection.server.error = ""
await this.notifyWebviewOfServerChanges()
await delay(500) // artificial delay to show user that server is restarting
```
```ts
// :1274-1282 — config survives via its serialized snapshot; revalidated AFTER delete
await this.deleteConnection(serverName, connection.server.source)
const parsedConfig = JSON.parse(config)
const validatedConfig = this.validateServerConfig(parsedConfig, serverName)
await this.connectToServer(serverName, validatedConfig, connection.server.source || "global")
```
```ts
// :1345-1354 — full-refresh shape: copy-on-iterate delete of EVERYTHING, then both sources re-init
const existingConnections = [...this.connections]
for (const conn of existingConnections) { await this.deleteConnection(conn.server.name, conn.server.source) }
await this.initializeMcpServers("global")
await this.initializeMcpServers("project")
```

**Flow:** restart = notify → status connecting → 500 ms deliberate pause (comment: so the user SEES the restart) → delete → re-parse+revalidate stored config → connectToServer → success/failure toasts; guarded by global-disable early-return (:1258–1262). refreshAll = disabled-fork (placeholders only) or isConnecting-guarded wipe-then-rebuild with `delay(100)` before notify; handleMcpEnabledChange funnels BOTH toggle directions through it (disable path collects per-server disconnection errors into a summary warning first :1904–1929).
**Invariant:** single-server restarts must reuse the STORED config snapshot (not the raw file) because file and memory can diverge mid-session; full refresh must iterate over a COPY of connections (array mutation during deletion). The 100ms settle delay before notify lets freshly-pushed connections stabilize their first capability fetches.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts`: it `"should skip restarting connection when MCP is disabled"` (:1978–2021) pins the disable gate; it `"should disconnect all servers when MCP is toggled from enabled to disabled"` (:1743–1821) pins the wipe path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "restartConnection refreshAllConnections initializeMcpServers", limit: 5 });
// Method rows McpHub.restartConnection 1254-1294 / refreshAllConnections 1296-1364 resolve in the updateServerConnections query family
```

## Verdict
Adopt stored-snapshot restart semantics and copy-before-wipe refresh. Adapt toast/UX delays freely (the 500ms is product, not contract — but keep SOME yield or rapid toggles visually flicker). Omit i18n plumbing.
