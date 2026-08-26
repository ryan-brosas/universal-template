<!-- capsule-v2 -->
# updateServerConnections deepEqual reconcile — how do you converge live connections with a new config map so unchanged servers never restart and removed servers always tear down?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the diff-and-reconcile algorithm between desired server config (file) and actual connections (memory)?

## Delete-removed → add-new → reconnect-only-if-deepEqual-differs → notify once
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`updateServerConnections` :1109–1176; watcher entry `handleConfigFileChange` :324–360; per-server file watchers :1178–1252).
**Signature:** `async updateServerConnections(newServers: Record<string, any>, source: "global" | "project" = "global", manageConnectingState = true): Promise<void>`.
**Data Shape:** operates ONLY on the given source's slice (`conn.server.source === source || (!source && source === "global")`); invalid configs are skipped with an error message, NOT fatal to the batch (:1141–1144 `continue`).

### Decisive source
```ts
// :1125-1130 — removals first
for (const name of currentNames) {
    if (!newNames.has(name)) { await this.deleteConnection(name, source) }
}
```
```ts
// :1157-1170 — the load-bearing comparison
} else if (!deepEqual(JSON.parse(currentConnection.server.config), config)) {
    // Existing server with changed config
    await this.deleteConnection(name, source)
    await this.connectToServer(name, validatedConfig, source)
}
// If server exists with same config, do nothing
```
```ts
// :1117 — watchers torn down wholesale then rebuilt only for enabled+changed servers
this.removeAllFileWatchers()
```

**Flow:** set `isConnecting` (if managing) → removeAllFileWatchers → compute name sets for this source → delete disappeared → validate each incoming config (bad = skip + report) → new names connect; existing names compare stored-config JSON vs raw new config via fast-deep-equal and rebuild ONLY on drift → single `notifyWebviewOfServerChanges()` at the end → clear isConnecting.
**Invariant:** no-change MUST mean no-reconnect (deepEqual gate) because every reconnect kills in-flight tool calls; validation failure isolates to one server while the rest of the file still applies; chokidar watchPaths/build/index.js watchers (:1191–1238) are rebuilt by the same pass — they exist ONLY for stdio servers and restart the server when its build output or explicit watchPaths change on disk.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts`: it `"should clean up all file watchers when server is deleted"` (:413–486), it `"should not create file watchers for disabled servers on initialization"` (:487–514); describe `"MCP global enable/disable"` it `"should handle refreshAllConnections when MCP is disabled"` (:1931–1977) pins the disabled-path fork of the same reconcile.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "updateServerConnections debounce config file change", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.debounceConfigChange 301-322; Method row McpHub.updateServerConnections 1109-1176 resolves in the same query family (total: 389)
```

## Verdict
Adopt delete→add→conditional-rebuild ordering with per-server error isolation. Adapt the deepEqual library freely. Omit nothing — the no-change-no-restart gate is what makes file watching survivable.
