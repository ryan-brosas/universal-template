<!-- capsule-v2 -->
# Global-vs-project MCP server precedence — how do you let a repo's .roo/mcp.json override a user-global server of the same name without forking the connection state?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When the same server name exists in both global settings and project config, which one wins at lookup, listing, ordering, and delete — and how is that enforced with ONE connection array?

## One array, source-tagged; project wins everywhere by explicit checks
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`getServers` :453–471 dedupe; `findConnection` :931–948 lookup order; `notifyWebviewOfServerChanges` sort comparator :1386–1405; `cleanupProjectMcpServers` :441–451).
**Signature:** `private findConnection(serverName: string, source?: "global" | "project"): McpConnection | undefined`.
**Data Shape:** `connections: McpConnection[]` holds BOTH sources simultaneously, each entry tagged `server.source: "global" | "project"` (falsy treated as global in every comparison). Config files: global `cline_mcp_settings.json`, project `<workspace>/.roo/mcp.json`.

### Decisive source
```ts
// :937-947 — lookup prefers project explicitly
// If no source is specified, first look for project servers, then global servers
// This ensures that when servers have the same name, project servers are prioritized
const projectConn = this.connections.find((conn) => conn.server.name === serverName && conn.server.source === "project")
if (projectConn) return projectConn
return this.connections.find(
    (conn) => conn.server.name === serverName && (conn.server.source === "global" || !conn.server.source),
)
```
```ts
// :462-466 — getServers dedupe: first-seen kept UNLESS an existing non-project meets a project twin
if (!existing) { serversByName.set(conn.server.name, conn.server) }
else if (conn.server.source === "project" && existing.source !== "project") {
    serversByName.set(conn.server.name, conn.server)   // Project server overrides global
}
```
```ts
// :1403-1404 — display ordering: project servers sort before global
// Project servers come before global servers (reversed from original)
return aIsGlobal ? 1 : -1
```

**Flow:** connections from both files coexist in one array → name-keyed consumers resolve project-first (`findConnection`, `getServers`) → webview list sorted project-block-then-global-block, each block in its own file's declaration order (read fresh from disk inside notify) → deleting `.roo/mcp.json` triggers `cleanupProjectMcpServers()` which deletes each project connection and re-runs `updateServerConnections({}, "project", false)`.
**Invariant:** precedence must be enforced at EVERY consumer (lookup, dedup, sort), not by removing globals — the global connection stays live so un-shadowing (project file deleted) needs no reconnect. Any new name-keyed accessor added to a port must replicate the project-first check or it silently flips precedence.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"server disabled state"` → its `"should deduplicate servers by name with project servers taking priority"` (:1279–1335) and `"should keep global server when no project server with same name exists"` (:1336–1359) pin both directions of `getServers`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "McpHub findConnection project global source precedence", limit: 5 });
// Method row McpHub.findConnection src/services/mcp/McpHub.ts 931-948 resolves under the connectToServer/validateServerConfig query family (same class cluster, total ≥7)
```

## Verdict
Adopt the single-array + per-consumer-precedence design. Adapt the config paths and the `.roo/mcp.json` location to your host. Omit the VSCode notification plumbing around cleanup.
